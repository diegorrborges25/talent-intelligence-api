# Arquitetura — Talent Intelligence API

## 1. Visão de camadas (implementado vs. alvo)

```
                      TALENT MARKET INTELLIGENCE LAYER
 ┌───────────── FONTES ─────────────┐
 │ ATS · LinkedIn · job boards      │   (alvo — Fase 2)
 │ planilhas · PDFs de currículos   │
 └───────────────┬──────────────────┘
                 ▼
        [Ingestão / Landing]            (alvo — Airbyte / Python / object storage)
                 ▼
        [Parsing documental]            (alvo — PyMuPDF/pdfplumber/OCR de currículos)
                 ▼
   ┌──────────────────────────────────────────────────┐
   │   CAMADA HÍBRIDA DE INTELIGÊNCIA  (IMPLEMENTADO)   │
   │   regras  →  similaridade  →  decisão  →  LLM opc. │
   └───────────────┬───────────────────────┬───────────┘
                   ▼                        ▼
        [Taxonomia mestre de cargos] [Índice de candidatos]
                   ▼                        ▼
   ┌──────────────────────────────────────────────────┐
   │  CAMADA ANALÍTICA  (IMPLEMENTADO — SQLite/stats)  │
   │  benchmark salarial · dispersão · outliers · gap  │
   └───────────────┬───────────────────────────────────┘
                   ▼
        [API REST /api/v1]  →  Swagger/ReDoc · BI · Copiloto (alvo)
```

O que está **implementado** nesta entrega: a camada híbrida de inteligência, a taxonomia
mestre de cargos, a camada analítica e a API REST versionada. As camadas de ingestão e
parsing documental são o caminho de evolução (Fases 2–3).

## 2. Componentes da aplicação

| Módulo | Responsabilidade |
|---|---|
| `app/main.py` | Bootstrap FastAPI, lifespan (init DB), middleware (request_id + acesso), versionamento. |
| `app/config.py` | Configuração 12-factor via `pydantic-settings`. |
| `app/logging_config.py` | Logging estruturado JSON, `request_id` por requisição, rotação em arquivo. |
| `app/database.py` | Conexão SQLite, esquema e disparo do seed. |
| `app/security.py` | Hashing PBKDF2 e emissão/validação de JWT. |
| `app/schemas.py` | Contratos Pydantic (validação de entrada/saída). |
| `app/errors.py` | Hierarquia de exceções e handlers com envelope padronizado. |
| `app/ai/extractor.py` | Extração determinística de atributos (skills, senioridade, anos, formação). |
| `app/ai/similarity.py` | Similaridade textual leve (Jaccard + sequência), sem deps. |
| `app/ai/classifier.py` | Classificação taxonômica de cargos (Serviço 1). |
| `app/ai/benchmark.py` | Estatística salarial, dispersão e outliers (Serviço 2). |
| `app/ai/matcher.py` | Decisão de aderência candidato × vaga (Serviço 3). |
| `app/ai/llm.py` | Enriquecimento opcional por Claude, com fallback. |
| `app/api/v1/*` | Rotas versionadas (auth, parse_resume, salary_benchmark, match, meta). |

## 3. Esquema de dados (implementado)

```sql
users(id, username, password_hash, role)

role_taxonomy(role_id, area, track, specialization,
              canonical_label, keywords, default_currency)

salary_observation(obs_id, role_id→role_taxonomy,
                   canonical_name, company, source, region,
                   seniority, currency, monthly_salary, observation_date)
```

A taxonomia tem 10 nós em 5 áreas (Tecnologia, Dados, Produto, Design, Marketing). As
observações salariais são sintéticas, geradas com semente fixa (`random.seed(42)`), com
dispersão controlada por senioridade e outliers propositais para exercitar o benchmark.

## 4. Modelo lógico-alvo (Fases 2–3)

Para suportar BI **e** IA juntos, o modelo evolui para incluir repositório documental e
índice vetorial, mantendo rastreabilidade de cada fato analítico até o documento e o trecho
de evidência (`document`, `document_chunk`, `entity_extraction`, `fact_salary_observation`,
`llm_run`, `human_review_queue`, etc.).

## 5. Fluxo de uma requisição

```
Cliente → [middleware: gera request_id + cronômetro]
        → [rota /api/v1/... : valida JWT + rate limit]
        → [Pydantic: valida corpo] (falha → 422 padronizado)
        → [serviço de IA em app/ai/*]
        → [resposta + header X-Request-ID]
        → [log de acesso JSON: método, path, status, latency_ms, request_id]
```
