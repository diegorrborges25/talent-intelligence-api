# Talent Intelligence API

**Camada de inteligência de talentos**, exposta como uma **API REST de IA** construída
em **FastAPI**.

Projeto duplo:
- **Trabalho final da disciplina _Construção de APIs para Inteligência Artificial_ (UFG — Módulo 3)** — uma API funcional com múltiplos serviços de IA, autenticação, versionamento, logs, validação e tratamento de erros.
- **Ferramenta de inteligência de recrutamento para a consultoria Nexa Talent** — transforma descrições caóticas de currículos e vagas em dados estruturados, comparáveis e analisáveis (benchmark salarial, dispersão, aderência candidato × vaga).

> A API roda **100% offline**, sem chave de LLM e sem banco externo (usa SQLite + motor de regras/similaridade). O enriquecimento por LLM (Claude) é **opcional**.

---

## 🚀 Início rápido (3 passos)

Pré-requisito: **Python 3.10+** (testado em 3.13).

```bash
# 1. Criar ambiente e instalar dependências
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
pip install -r requirements.txt

# 2. (Opcional) Copiar configuração — a API roda sem isso, com defaults seguros
cp .env.example .env

# 3. Subir a API (o banco é criado e populado automaticamente no 1º start)
uvicorn app.main:app --reload
```

Acesse:
- **Documentação interativa (Swagger):** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc
- **Health check:** http://127.0.0.1:8000/api/v1/health

Credenciais de demonstração: **usuário `recruiter` / senha `talent123`**.

---

## 🔐 Autenticação (em 10 segundos)

Todos os endpoints de IA exigem **Bearer Token (JWT)**. Pelo Swagger, clique em
**Authorize** e informe `recruiter` / `talent123`. Via terminal:

```bash
# 1. Obter token
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/token \
  -d "username=recruiter&password=talent123" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 2. Chamar um serviço de IA
curl -X POST http://127.0.0.1:8000/api/v1/parse-resume \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Engenheiro de software sênior com 8 anos em Python, FastAPI e AWS"}'
```

---

## 🧠 Serviços de IA (3 endpoints, operações distintas)

| Endpoint | Operação de IA | O que faz |
|---|---|---|
| `POST /api/v1/parse-resume` | **NLP / extração + classificação** | Estrutura um currículo livre em perfil + cargo taxonômico, com skills, senioridade, formação, evidências e confiança. |
| `POST /api/v1/salary-benchmark` | **Análise / estatística** | Calcula mediana, p25/p75, dispersão (CV), outliers (IQR) e gap vs. oferta. |
| `POST /api/v1/match` | **Decisão / similaridade** | Decide a aderência de um candidato a uma vaga (FIT/REVIEW/NO_FIT). |

Endpoints de apoio: `GET /api/v1/health`, `GET /api/v1/taxonomy`, `POST /api/v1/auth/token`.

### Exemplo — parse de currículo

Request:
```json
{ "text": "Engenheiro de software sênior com 8 anos de experiência em Python, Django, FastAPI, AWS e Docker. Mestrado em Ciência da Computação. Inglês avançado. Modelo remoto." }
```
Response (resumo):
```json
{
  "canonical_name": "Sênior Engenheiro(a) de Software Backend",
  "area": "Tecnologia",
  "track": "Engenharia de Software",
  "specialization": "Backend",
  "role_path": "TECNOLOGIA > ENGENHARIA DE SOFTWARE > BACKEND",
  "seniority": "Sênior", "years_experience": 8,
  "education_level": "Mestrado",
  "skills": ["Python", "Django", "FastAPI", "AWS", "Docker"],
  "languages": ["Inglês"], "work_mode": "remoto",
  "decision": "MATCH", "confidence": 1.0,
  "evidence": [ {"field":"skill","text":"Python"}, ... ],
  "engine": "regras+similaridade"
}
```

### Exemplo — benchmark salarial
```json
{ "description": "cientista de dados machine learning", "seniority": "Júnior", "offered_salary": 15000 }
```
Retorna estatísticas, `by_company`, `by_region`, `by_seniority`, `outliers` e
`offer_assessment` (gap da oferta vs. a mediana de mercado).

### Exemplo — match candidato × vaga
```json
{ "resume": "Backend sênior 8 anos Python FastAPI Docker AWS",
  "job": "Vaga backend sênior: Python, FastAPI, Kubernetes, AWS. 5+ anos." }
```
Retorna `skill_match`, `matched_skills`, `missing_skills`, `critical_gaps` e a
`decision` (FIT/REVIEW/NO_FIT).

---

## 🏗️ Como funciona (pipeline híbrido)

```
texto livre (currículo / vaga)
   │
   ▼
[1] Regras determinísticas  → skills, anos de exp., senioridade, formação, idiomas (+ evidências)
   │
   ▼
[2] Similaridade textual    → recupera candidatos da taxonomia de cargos (Jaccard + sequência)
   │
   ▼
[3] Decisão por limiar      → MATCH / REVIEW / NO_MATCH + score de confiança
   │
   ▼
[4] (opcional) LLM Claude   → refina cargo canônico/atributos — com fallback automático
```

O LLM **nunca decide sozinho** e **nunca quebra a API**: sem chave, sem lib ou em caso de
erro, o sistema segue com regras + similaridade. Isso espelha a boa prática de
*human-in-the-loop* e classificação assistida.

---

## ✅ Requisitos da disciplina — onde cada um está

| Critério UFG | Implementação |
|---|---|
| **≥ 2 serviços de IA distintos** | 3 endpoints: parse de currículo (NLP), benchmark salarial (analítico), match (decisão). |
| **Validação de dados** | Schemas Pydantic v2 (`app/schemas.py`) com limites e tipos → 422 padronizado. |
| **Tratamento de erros** | Handlers centralizados + envelope único (`app/errors.py`). |
| **Logs** | JSON estruturado + `request_id` + log de acesso com latência (`app/logging_config.py`). |
| **Segurança** | JWT (PyJWT), senhas com PBKDF2, rate limiting (`app/security.py`, `app/api/deps.py`). |
| **Versionamento** | Prefixo `/api/v1` + versão no health (`app/main.py`). |
| **Documentação** | OpenAPI automático (`/docs`, `/redoc`) + este README + roteiro executivo. |
| **Executa em outra máquina** | Apenas `pip install -r requirements.txt`; SQLite + seed automático; sem serviços externos. |

---

## 🧪 Testes

```bash
pip install -r requirements-dev.txt
pytest
```
22 testes cobrindo cenários válidos e inválidos (auth, parse, benchmark,
match, validação, health).

---

## 📁 Estrutura

```
talent-intelligence-api/
├── app/
│   ├── main.py            # FastAPI: lifespan, middleware, versionamento
│   ├── config.py          # settings (12-factor)
│   ├── logging_config.py  # logs JSON + request_id
│   ├── database.py        # SQLite (schema + seed automático)
│   ├── security.py        # JWT + hashing PBKDF2
│   ├── schemas.py         # contratos Pydantic (validação)
│   ├── errors.py          # exceções + handlers
│   ├── ai/                # extractor, classifier, benchmark, matcher, similarity, llm
│   └── api/v1/            # rotas versionadas
├── data/seed_talent.py    # taxonomia de cargos + observações salariais sintéticas
├── tests/                 # suíte pytest
├── docs/                  # ROTEIRO_EXECUTIVO.md + ARQUITETURA.md
├── requirements.txt
└── .env.example
```

---

## 🤖 Ativando o LLM (opcional)

1. `pip install anthropic`
2. No `.env`, defina `ANTHROPIC_API_KEY=...`
3. Reinicie a API. O parsing passa a usar `engine: "regras+similaridade+llm"`.

Sem essas etapas, tudo continua funcionando offline.

---

## 📜 Licença
MIT.
