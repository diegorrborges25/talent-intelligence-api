"""Match candidato × vaga (Serviço de IA nº 3).

Distingue "mesma trilha de cargo" de "aderência real à vaga". Um candidato só é
FIT quando está na mesma trilha/área E suas skills cobrem as exigências, sem
lacunas críticas (senioridade abaixo ou anos de experiência insuficientes).
"""

import re
import sqlite3

from .classifier import classify
from .extractor import extract_skills
from .similarity import jaccard, tokens

_SENIORITY_RANK = {
    "Estágio": 0, "Júnior": 1, "Pleno": 2, "Sênior": 3, "Especialista": 4,
}

_REQ_YEARS = re.compile(r"(\d{1,2})\s*\+?\s*anos?", re.IGNORECASE)


def _critical_gaps(resume: dict, job: dict, missing_skills: list[str], job_text: str) -> list[str]:
    gaps: list[str] = []

    # Senioridade do candidato abaixo da exigida pela vaga.
    rs, js = resume.get("seniority"), job.get("seniority")
    if rs and js and _SENIORITY_RANK.get(rs, 99) < _SENIORITY_RANK.get(js, -1):
        gaps.append(f"senioridade abaixo do exigido ({rs} vs {js})")

    # Anos de experiência exigidos pela vaga vs. os do candidato.
    req_years = [int(m.group(1)) for m in _REQ_YEARS.finditer(job_text)]
    if req_years:
        required = max(req_years)
        candidate_years = resume.get("years_experience")
        if candidate_years is not None and candidate_years < required:
            gaps.append(
                f"experiência abaixo do exigido ({candidate_years} vs {required} anos)"
            )

    # Skills críticas ausentes (limita a 5 para legibilidade).
    if missing_skills:
        gaps.append("skills ausentes: " + ", ".join(missing_skills[:5]))

    return gaps


def match(resume_text: str, job_text: str, conn: sqlite3.Connection) -> dict:
    """Avalia a aderência de um currículo a uma vaga."""
    cr = classify(resume_text, conn, use_llm=False)
    cj = classify(job_text, conn, use_llm=False)

    same_track = (
        cr.get("role_id") is not None and cr.get("role_id") == cj.get("role_id")
    )

    resume_skills = extract_skills(resume_text)
    job_skills = extract_skills(job_text)
    matched = [s for s in job_skills if s in set(resume_skills)]
    missing = [s for s in job_skills if s not in set(resume_skills)]

    if job_skills:
        skill_match = round(jaccard(set(resume_skills), set(job_skills)), 4)
    else:
        # Sem skills explícitas na vaga: usa similaridade textual como proxy.
        skill_match = round(
            jaccard(tokens(resume_text), tokens(job_text)), 4
        )

    gaps = _critical_gaps(cr, cj, missing, job_text)
    blocking_gaps = [g for g in gaps if not g.startswith("skills ausentes")]

    if same_track and skill_match >= 0.6 and not gaps:
        decision = "FIT"
        rationale = "Mesma trilha de cargo e skills cobrindo as exigências da vaga."
    elif same_track and skill_match >= 0.3 and not blocking_gaps:
        decision = "REVIEW"
        rationale = "Mesma trilha, mas com lacunas de skills a validar em entrevista."
    elif same_track:
        decision = "REVIEW"
        rationale = "Mesma trilha, porém com lacunas críticas (senioridade/experiência)."
    else:
        decision = "NO_FIT"
        rationale = "Trilhas de cargo distintas ou aderência de skills insuficiente."

    confidence = round(
        min(cr["confidence"], cj["confidence"]) * (0.5 + 0.5 * skill_match), 4
    )

    return {
        "resume_role": cr["canonical_name"],
        "job_role": cj["canonical_name"],
        "same_track": same_track,
        "role_resume": cr.get("role_path"),
        "role_job": cj.get("role_path"),
        "skill_match": skill_match,
        "matched_skills": matched,
        "missing_skills": missing,
        "decision": decision,
        "critical_gaps": gaps,
        "rationale": rationale,
        "confidence": confidence,
    }
