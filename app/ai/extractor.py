"""Extração determinística de atributos de perfis profissionais (motor de regras).

Esta é a primeira etapa do pipeline híbrido (regras -> similaridade -> LLM).
Regras determinísticas são baratas, auditáveis e não alucinam; por isso resolvem
skills, anos de experiência, senioridade, formação, idiomas e modelo de trabalho
antes de qualquer modelo. Cada atributo extraído vem com seu trecho de evidência.
"""

import re
import unicodedata

# Dicionário de skills: chave normalizada (sem acento, minúscula) -> forma canônica.
# Inclui termos multi-palavra (ex.: "machine learning") e símbolos (c#, c++, node.js).
_SKILLS = {
    "python": "Python", "java": "Java", "javascript": "JavaScript",
    "typescript": "TypeScript", "c#": "C#", "c++": "C++", ".net": ".NET",
    "go": "Go", "golang": "Go", "rust": "Rust", "ruby": "Ruby", "php": "PHP",
    "scala": "Scala", "kotlin": "Kotlin", "swift": "Swift",
    "sql": "SQL", "nosql": "NoSQL", "postgresql": "PostgreSQL", "postgres": "PostgreSQL",
    "mysql": "MySQL", "mongodb": "MongoDB", "redis": "Redis", "snowflake": "Snowflake",
    "redshift": "Redshift", "bigquery": "BigQuery", "elasticsearch": "Elasticsearch",
    "react": "React", "angular": "Angular", "vue": "Vue", "node.js": "Node.js",
    "nodejs": "Node.js", "node": "Node.js", "django": "Django", "fastapi": "FastAPI",
    "flask": "Flask", "spring": "Spring", "express": "Express", "graphql": "GraphQL",
    "rest": "REST", "html": "HTML", "css": "CSS",
    "aws": "AWS", "azure": "Azure", "gcp": "GCP", "docker": "Docker",
    "kubernetes": "Kubernetes", "k8s": "Kubernetes", "terraform": "Terraform",
    "linux": "Linux", "git": "Git", "ci/cd": "CI/CD", "cicd": "CI/CD",
    "kafka": "Kafka", "spark": "Spark", "hadoop": "Hadoop", "airflow": "Airflow",
    "dbt": "dbt", "etl": "ETL", "pandas": "Pandas", "numpy": "NumPy",
    "tensorflow": "TensorFlow", "pytorch": "PyTorch", "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn", "machine learning": "Machine Learning",
    "deep learning": "Deep Learning", "nlp": "NLP", "power bi": "Power BI",
    "powerbi": "Power BI", "tableau": "Tableau", "looker": "Looker", "excel": "Excel",
    "figma": "Figma", "sketch": "Sketch", "adobe xd": "Adobe XD",
    "jira": "Jira", "scrum": "Scrum", "kanban": "Kanban", "agile": "Agile",
    "product discovery": "Product Discovery", "roadmap": "Roadmap",
    "seo": "SEO", "google ads": "Google Ads", "meta ads": "Meta Ads",
}

# Senioridade explícita (palavra -> rótulo canônico). Ordem importa na varredura.
_SENIORITY = [
    (r"\bestag[ií]ári[oa]\b|\best[áa]gio\b", "Estágio"),
    (r"\bespecialista\b|\bstaff\b|\bprincipal\b|\btech\s*lead\b|\blíder\s+técnic[oa]\b", "Especialista"),
    (r"\bs[êe]nior\b|\bsenior\b|\bsr\.?\b", "Sênior"),
    (r"\bpleno\b|\bpl\.?\b", "Pleno"),
    (r"\bj[úu]nior\b|\bjunior\b|\bjr\.?\b", "Júnior"),
]

# Formação (regex -> rótulo). Mais alto tem prioridade.
_EDUCATION = [
    (r"\bdoutorad[oa]\b|\bph\.?d\b|\bdoutor[ao]?\b", "Doutorado"),
    (r"\bmestrad[oa]\b|\bmestr[ae]\b", "Mestrado"),
    (r"\bmba\b|\bp[óo]s[\s\-]?gradua[çc][ãa]o\b|\bespecializa[çc][ãa]o\b", "Pós-graduação"),
    (r"\bgradua[çc][ãa]o\b|\bbachar[ae]l\b|\bsuperior\s+complet[oa]\b|\blicenciatura\b", "Graduação"),
    (r"\bt[ée]cnic[oa]\b|\bensino\s+t[ée]cnico\b", "Técnico"),
]

_LANGUAGES = [
    (r"\bingl[êe]s\b|\benglish\b", "Inglês"),
    (r"\bespanhol\b|\bspanish\b|\bespa[ñn]ol\b", "Espanhol"),
    (r"\bfranc[êe]s\b|\bfrench\b", "Francês"),
    (r"\balem[ãa]o\b|\bgerman\b", "Alemão"),
]

_WORK_MODE = [
    (r"\bremot[oa]\b|\bremote\b|\bhome\s*office\b", "remoto"),
    (r"\bh[íi]brid[oa]\b|\bhybrid\b", "híbrido"),
    (r"\bpresencial\b|\bon[\s\-]?site\b", "presencial"),
]

_YEARS = re.compile(r"(\d{1,2})\s*\+?\s*anos?", re.IGNORECASE)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def extract_skills(text: str) -> list[str]:
    """Retorna a lista de skills canônicas encontradas, preservando a 1ª ocorrência."""
    norm = _norm(text)
    found: list[str] = []
    seen: set[str] = set()
    # Ordena chaves por tamanho decrescente para casar multi-palavra antes de tokens.
    for key in sorted(_SKILLS, key=len, reverse=True):
        pattern = rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])"
        if re.search(pattern, norm):
            canonical = _SKILLS[key]
            if canonical not in seen:
                seen.add(canonical)
                found.append(canonical)
    return found


def extract_attributes(text: str) -> dict:
    """Retorna {'attributes': {...}, 'skills': [...], 'evidence': [...]}."""
    desc = text.strip()
    norm = _norm(desc)
    attributes: dict = {}
    evidence: list[dict] = []

    # --- Skills ---
    skills = extract_skills(desc)
    for sk in skills:
        evidence.append({"field": "skill", "text": sk})

    # --- Anos de experiência (pega o maior valor citado) ---
    years_found = [int(m.group(1)) for m in _YEARS.finditer(norm)]
    years = max(years_found) if years_found else None
    if years is not None:
        attributes["years_experience"] = years
        evidence.append({"field": "years_experience", "text": f"{years} anos"})

    # --- Senioridade (explícita; senão inferida pelos anos) ---
    seniority = None
    for pattern, label in _SENIORITY:
        if re.search(pattern, norm):
            seniority = label
            evidence.append({"field": "seniority", "text": label})
            break
    if seniority is None and years is not None:
        if years < 2:
            seniority = "Júnior"
        elif years < 5:
            seniority = "Pleno"
        elif years < 9:
            seniority = "Sênior"
        else:
            seniority = "Especialista"
        evidence.append({"field": "seniority", "text": f"inferida de {years} anos"})
    if seniority:
        attributes["seniority"] = seniority

    # --- Formação (maior nível citado) ---
    for pattern, label in _EDUCATION:
        if re.search(pattern, norm):
            attributes["education_level"] = label
            evidence.append({"field": "education_level", "text": label})
            break

    # --- Idiomas ---
    languages: list[str] = []
    for pattern, label in _LANGUAGES:
        if re.search(pattern, norm):
            languages.append(label)
            evidence.append({"field": "language", "text": label})
    if languages:
        attributes["languages"] = languages

    # --- Modelo de trabalho ---
    for pattern, label in _WORK_MODE:
        if re.search(pattern, norm):
            attributes["work_mode"] = label
            evidence.append({"field": "work_mode", "text": label})
            break

    return {"attributes": attributes, "skills": skills, "evidence": evidence}
