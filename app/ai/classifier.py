"""Classificador taxonômico híbrido de cargos (Serviço de IA nº 1).

Pipeline:
  1) regras determinísticas  -> extrai skills/atributos/evidências;
  2) recuperação de candidatos -> similaridade contra a taxonomia mestre de cargos;
  3) decisão                  -> MATCH / REVIEW / NO_MATCH por limiar de confiança;
  4) (opcional) LLM           -> refina nome canônico e atributos, com fallback.

A confiança final combina a força da melhor correspondência com a margem em relação
ao segundo candidato (separabilidade), penalizando casos ambíguos.
"""

import logging
import sqlite3

from .extractor import extract_attributes
from .llm import enrich_parsing
from .similarity import similarity

logger = logging.getLogger("talent.ai.classifier")

_MATCH_THRESHOLD = 0.40
_REVIEW_THRESHOLD = 0.22
_TOP_K = 3


def _load_taxonomy(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT role_id, area, track, specialization, canonical_label, "
        "keywords, default_currency FROM role_taxonomy"
    ).fetchall()
    return [dict(r) for r in rows]


def _path(node: dict) -> str:
    parts = [node["area"], node["track"]]
    if node.get("specialization"):
        parts.append(node["specialization"])
    return " > ".join(p.upper() for p in parts if p)


def _score_node(text: str, skills: list[str], node: dict) -> float:
    """Score de aderência: melhor entre o rótulo canônico, keywords e skills."""
    target_label = f"{node['track']} {node.get('specialization') or ''} {node['canonical_label']}"
    best = similarity(text, target_label)
    keywords = [kw.strip() for kw in node["keywords"].split(",") if kw.strip()]
    for kw in keywords:
        best = max(best, similarity(text, kw))
    # Bônus por skills do perfil que aparecem nas keywords do nó (overlap direto).
    if skills:
        kw_norm = {k.lower() for k in keywords}
        hits = sum(1 for s in skills if s.lower() in kw_norm)
        if hits:
            best = max(best, min(1.0, 0.45 + 0.12 * hits))
    return round(best, 4)


def _build_canonical(text: str, attrs: dict, node: dict | None) -> str:
    """Monta um nome canônico curto a partir de senioridade + cargo."""
    if node:
        base = node["canonical_label"]
    else:
        base = text.strip()[:60]
    seniority = attrs.get("seniority")
    if seniority and node and seniority.lower() not in base.lower():
        return f"{seniority} {base}".strip()
    return base.strip()


def classify(text: str, conn: sqlite3.Connection, use_llm: bool = True) -> dict:
    """Classifica um perfil/cargo e devolve o dicionário pronto p/ ParseResumeResponse."""
    extracted = extract_attributes(text)
    attrs = extracted["attributes"]
    skills = extracted["skills"]
    evidence = list(extracted["evidence"])

    taxonomy = _load_taxonomy(conn)
    scored = sorted(
        ({"node": n, "score": _score_node(text, skills, n)} for n in taxonomy),
        key=lambda x: x["score"],
        reverse=True,
    )
    top = scored[:_TOP_K]
    best = top[0] if top else None
    best_score = best["score"] if best else 0.0
    second_score = top[1]["score"] if len(top) > 1 else 0.0

    # Decisão por limiar + separabilidade.
    if best_score >= _MATCH_THRESHOLD:
        decision = "MATCH"
    elif best_score >= _REVIEW_THRESHOLD:
        decision = "REVIEW"
    else:
        decision = "NO_MATCH"

    margin = best_score - second_score
    # Confiança: força do melhor candidato, ajustada pela margem de separação.
    confidence = round(min(1.0, best_score * (0.7 + 0.3 * min(margin / 0.2, 1.0))), 4)
    if decision == "NO_MATCH":
        confidence = round(best_score, 4)

    node = best["node"] if (best and decision != "NO_MATCH") else None
    ambiguity_note = None
    if decision == "REVIEW":
        ambiguity_note = (
            "Baixa separabilidade entre candidatos — recomenda-se revisão humana."
        )

    canonical = _build_canonical(text, attrs, node)
    engine = "regras+similaridade"

    result = {
        "raw_text": text,
        "canonical_name": canonical,
        "area": node["area"] if node else None,
        "track": node["track"] if node else None,
        "specialization": node.get("specialization") if node else None,
        "role_id": node["role_id"] if node else None,
        "role_path": _path(node) if node else None,
        "seniority": attrs.get("seniority"),
        "years_experience": attrs.get("years_experience"),
        "education_level": attrs.get("education_level"),
        "skills": skills,
        "languages": attrs.get("languages", []),
        "work_mode": attrs.get("work_mode"),
        "decision": decision,
        "confidence": confidence,
        "candidates": [
            {"role_id": c["node"]["role_id"], "path": _path(c["node"]), "score": c["score"]}
            for c in top
        ],
        "evidence": evidence,
        "ambiguity_note": ambiguity_note,
        "engine": engine,
    }

    # Etapa opcional de LLM (refina sem nunca quebrar).
    if use_llm:
        refined = enrich_parsing(text, {
            "canonical_name": canonical,
            "seniority": attrs.get("seniority"),
            "area": result["area"],
        })
        if refined:
            if refined.get("canonical_name"):
                result["canonical_name"] = refined["canonical_name"]
            if refined.get("seniority") and not result["seniority"]:
                result["seniority"] = refined["seniority"]
            if refined.get("ambiguity_note"):
                result["ambiguity_note"] = refined["ambiguity_note"]
            result["engine"] = "regras+similaridade+llm"

    return result
