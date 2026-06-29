"""Similaridade textual leve, 100% stdlib (sem numpy/embeddings pesados).

Para classificar uma descrição contra a taxonomia de cargos, combinamos dois sinais:
  - Jaccard de tokens normalizados (overlap de vocabulário);
  - difflib.SequenceMatcher (similaridade de sequência de caracteres).
Isso emula o papel de "recuperação de candidatos por embeddings", mas sem
dependências externas — garantindo que a API rode em qualquer máquina.
"""

import re
import unicodedata
from difflib import SequenceMatcher

_STOPWORDS = {
    "de", "da", "do", "para", "com", "sem", "em", "e", "ou", "a", "o", "um",
    "uma", "anos", "ano", "experiencia", "vaga", "profissional", "atuacao",
}


def normalize(text: str) -> str:
    """Minúsculas, sem acento, pontuação virando espaço."""
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9\.\+\#\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokens(text: str) -> set[str]:
    """Tokeniza removendo stopwords e tokens muito curtos."""
    out = set()
    for tok in normalize(text).split():
        if tok in _STOPWORDS:
            continue
        if len(tok) <= 1:
            continue
        out.add(tok)
    return out


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def similarity(query: str, target: str) -> float:
    """Score combinado em [0, 1]: 0.65*Jaccard de tokens + 0.35*sequência."""
    q_norm, t_norm = normalize(query), normalize(target)
    seq = SequenceMatcher(None, q_norm, t_norm).ratio()
    jac = jaccard(tokens(query), tokens(target))
    return round(0.65 * jac + 0.35 * seq, 4)
