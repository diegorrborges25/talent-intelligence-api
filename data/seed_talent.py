"""Seed determinístico do banco de inteligência de talentos.

Cria o usuário de demonstração, a taxonomia mestre de cargos (10 nós / 5 áreas) e
observações salariais sintéticas porém realistas, com dispersão controlada por
senioridade e alguns outliers propositais — para que o benchmark e a detecção de
anomalias tenham o que analisar. Tudo com `random.seed` fixo, garantindo
reprodutibilidade entre máquinas.
"""

import random
import sqlite3
from datetime import date, timedelta

from app.config import get_settings
from app.security import hash_password

# (area, track, specialization, canonical_label, keywords, default_currency)
TAXONOMY = [
    ("Tecnologia", "Engenharia de Software", "Backend",
     "Engenheiro(a) de Software Backend",
     "backend,python,java,fastapi,django,spring,node.js,sql,postgresql,docker,kubernetes,aws,api,microservicos", "BRL"),
    ("Tecnologia", "Engenharia de Software", "Frontend",
     "Engenheiro(a) de Software Frontend",
     "frontend,react,angular,vue,typescript,javascript,css,html,node.js,web", "BRL"),
    ("Tecnologia", "Engenharia de Software", "DevOps/SRE",
     "Engenheiro(a) DevOps / SRE",
     "devops,sre,docker,kubernetes,terraform,aws,azure,gcp,ci/cd,linux,infraestrutura,observabilidade", "BRL"),
    ("Tecnologia", "Engenharia de Software", "Mobile",
     "Engenheiro(a) Mobile",
     "mobile,android,ios,swift,kotlin,react native,aplicativo", "BRL"),
    ("Dados", "Ciência de Dados", "Machine Learning",
     "Cientista de Dados / ML",
     "data science,ciencia de dados,machine learning,deep learning,pytorch,tensorflow,scikit-learn,pandas,numpy,nlp,python,sql,modelo", "BRL"),
    ("Dados", "Engenharia de Dados", "Data Platform",
     "Engenheiro(a) de Dados",
     "engenharia de dados,data engineer,spark,kafka,airflow,dbt,etl,snowflake,redshift,bigquery,python,sql,pipeline", "BRL"),
    ("Dados", "Análise de Dados", "Business Intelligence",
     "Analista de Dados / BI",
     "analista de dados,bi,business intelligence,power bi,tableau,looker,excel,sql,python,etl,dashboard,kpi", "BRL"),
    ("Produto", "Gestão de Produto", "Product Management",
     "Product Manager",
     "produto,product manager,gestao de produto,roadmap,product discovery,scrum,kanban,jira,agile,backlog,metricas", "BRL"),
    ("Design", "Design de Produto", "UX/UI",
     "Designer de Produto (UX/UI)",
     "design,designer,ux,ui,user experience,figma,sketch,adobe xd,prototipagem,wireframe,usabilidade", "BRL"),
    ("Marketing", "Marketing Digital", "Performance",
     "Analista de Marketing Digital",
     "marketing,marketing digital,performance,seo,google ads,meta ads,growth,trafego pago,midia,campanha", "BRL"),
]

# role_id (1-based) -> (salário-base "Pleno" em BRL, coef. variação dentro da senioridade)
SALARY_PROFILE = {
    1: (12000, 0.12),
    2: (11000, 0.12),
    3: (13000, 0.13),
    4: (11500, 0.13),
    5: (14000, 0.14),
    6: (13000, 0.12),
    7: (8000, 0.13),
    8: (14000, 0.15),
    9: (9000, 0.13),
    10: (6500, 0.14),
}

# Multiplicador salarial por senioridade (sobre o salário-base "Pleno").
SENIORITY_MULT = {
    "Estágio": 0.35,
    "Júnior": 0.6,
    "Pleno": 1.0,
    "Sênior": 1.5,
    "Especialista": 2.0,
}
SENIORITIES = list(SENIORITY_MULT.keys())
OBS_PER_SENIORITY = 6  # 6 * 5 senioridades = 30 observações por cargo

COMPANIES = ["TechNova", "DataForge", "CloudPeak", "FinX", "HealthSys", "RetailOne", "LogiCorp", "MediaLab"]
REGIONS = ["Sudeste", "Sul", "Centro-Oeste", "Nordeste", "Norte"]
SOURCES = ["Glassdoor", "LinkedIn", "Catho", "Pesquisa Interna", "Vagas.com"]

# Outliers propositais: (role_id, empresa, região, senioridade, multiplicador sobre o salário daquela senioridade)
OUTLIERS = [
    (5, "FinX", "Sudeste", "Júnior", 3.6),       # cientista de dados júnior absurdamente caro
    (10, "MediaLab", "Norte", "Sênior", 0.3),    # marketing sênior anormalmente barato
    (1, "CloudPeak", "Sul", "Pleno", 2.7),       # backend pleno muito acima do mercado
]


def seed_database(conn: sqlite3.Connection) -> None:
    rng = random.Random(42)
    settings = get_settings()

    # --- Usuário demo ---
    conn.execute(
        "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (settings.demo_username, hash_password(settings.demo_password), "recruiter"),
    )

    # --- Taxonomia ---
    conn.executemany(
        "INSERT INTO role_taxonomy "
        "(area, track, specialization, canonical_label, keywords, default_currency) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        TAXONOMY,
    )

    # --- Observações salariais ---
    today = date(2026, 6, 1)
    rows = []
    for role_id, (base, cv) in SALARY_PROFILE.items():
        label = TAXONOMY[role_id - 1][3]
        currency = TAXONOMY[role_id - 1][5]
        for seniority, mult in SENIORITY_MULT.items():
            center = base * mult
            for _ in range(OBS_PER_SENIORITY):
                salary = max(1000.0, rng.gauss(center, center * cv))
                rows.append((
                    role_id, label,
                    rng.choice(COMPANIES), rng.choice(SOURCES),
                    rng.choice(REGIONS), seniority, currency, round(salary, 2),
                    (today - timedelta(days=rng.randint(0, 180))).isoformat(),
                ))

    for role_id, company, region, seniority, mult in OUTLIERS:
        base = SALARY_PROFILE[role_id][0]
        label = TAXONOMY[role_id - 1][3]
        currency = TAXONOMY[role_id - 1][5]
        center = base * SENIORITY_MULT[seniority]
        rows.append((
            role_id, label, company, rng.choice(SOURCES),
            region, seniority, currency, round(center * mult, 2),
            (today - timedelta(days=rng.randint(0, 60))).isoformat(),
        ))

    conn.executemany(
        "INSERT INTO salary_observation "
        "(role_id, canonical_name, company, source, region, "
        "seniority, currency, monthly_salary, observation_date) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
