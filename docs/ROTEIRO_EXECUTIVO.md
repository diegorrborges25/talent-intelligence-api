# Roteiro Executivo — Talent Intelligence API

> Documento-guia que explica **o que foi construído, como foi construído e como usar**,
> conectando o **trabalho final da UFG** (disciplina *Construção de APIs para IA*) ao
> **produto de inteligência de recrutamento** da consultoria **Nexa Talent**.

---

## 1. Objetivo duplo

Esta entrega resolve dois problemas ao mesmo tempo:

1. **Acadêmico (UFG):** desenvolver uma API funcional com **pelo menos dois serviços de IA**,
   demonstrando boas práticas — versionamento, autenticação, documentação, logs,
   tratamento de erros e validação.
2. **Consultivo (Nexa Talent):** entregar a **semente de uma plataforma de inteligência de
   talentos**, capaz de transformar descrições caóticas de currículos e vagas em dados
   estruturados, comparáveis e analisáveis — base para benchmark salarial e triagem.

A escolha do domínio de recrutamento atende explicitamente à orientação da disciplina de
usar "algo relacionado a uma situação real, como uma demanda do trabalho".

---

## 2. O que foi entregue

Uma **API REST em FastAPI** com:

- **3 serviços de IA** (operações distintas):
  1. `POST /api/v1/parse-resume` — **parse + classificação** de currículos (NLP/regras);
  2. `POST /api/v1/salary-benchmark` — **benchmark salarial, dispersão e outliers** (analítico);
  3. `POST /api/v1/match` — **decisão de aderência** candidato × vaga.
- **Autenticação JWT** (OAuth2 password flow) + senhas com hashing PBKDF2.
- **Versionamento** por prefixo `/api/v1`.
- **Documentação interativa** automática (Swagger `/docs` e ReDoc `/redoc`).
- **Logs estruturados** em JSON, com `request_id` e medição de latência por requisição.
- **Tratamento de erros** centralizado, com envelope de erro padronizado.
- **Validação de dados** via Pydantic v2.
- **Rate limiting** básico (proteção anti-abuso).
- **Banco SQLite** com taxonomia de cargos e observações salariais, **populado automaticamente**.
- **Suíte de testes** (pytest) com 22 casos, cobrindo entradas válidas e inválidas.
- **Integração opcional com LLM (Claude)** — enriquece o parsing, com fallback total.

---

## 3. Como foi construído — decisões e justificativas

### 3.1. Por que FastAPI
Sugerido pela disciplina, oferece de fábrica: validação por Pydantic, documentação OpenAPI,
injeção de dependências e suporte nativo a OAuth2/JWT. Reduz código repetitivo e já entrega
vários requisitos "de graça" (docs, validação).

### 3.2. Por que um pipeline híbrido (regras + similaridade + LLM opcional)
O LLM **não deve decidir sozinho**. Ele é um componente em um fluxo com regras
determinísticas, recuperação por similaridade e revisão humana. Implementamos exatamente isso:

- **Regras** resolvem o que é objetivo (skills, anos de experiência, senioridade, formação,
  idiomas, modelo de trabalho) — barato, auditável e sem alucinação;
- **Similaridade textual** recupera candidatos da taxonomia de cargos (papel dos "embeddings",
  feito com `difflib` + Jaccard para não exigir dependências pesadas);
- **Decisão por limiar** classifica em `MATCH` / `REVIEW` / `NO_MATCH` com score de
  confiança que penaliza ambiguidade (baixa separabilidade entre candidatos);
- **LLM (Claude)** é uma camada **opcional** de refino, que **nunca quebra** a API.

### 3.3. Por que SQLite + seed automático
O critério de avaliação exige que "o código execute em outro computador". Bancos como
Postgres exigiriam servidor e instalação. SQLite é embutido no Python e o seed roda no
startup — então **basta `pip install` e `uvicorn`** para a API funcionar em qualquer
máquina, com dados realistas para o benchmark.

### 3.4. Por que o LLM é opcional
Para garantir reprodutibilidade e zero fricção na avaliação (e zero custo), a API roda
offline por padrão. Quem quiser ativar o LLM define `ANTHROPIC_API_KEY` — o sistema detecta
e passa a usar `engine: "regras+similaridade+llm"`. Sem chave/lib/erro, há fallback automático.

### 3.5. Segurança em camadas
- Senhas nunca em texto puro (PBKDF2-HMAC-SHA256 com salt, via stdlib);
- Acesso aos serviços de IA somente com Bearer Token (JWT assinado, com expiração);
- Rate limiting por IP+token (janela de 60s);
- Erros internos nunca vazam stacktrace ao cliente (apenas via logs).

---

## 4. Como executar (passo a passo)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- Abra **http://127.0.0.1:8000/docs**
- Clique em **Authorize** → `recruiter` / `talent123`
- Teste `parse-resume`, `salary-benchmark` e `match` direto pela interface.

Rodar os testes: `pip install -r requirements-dev.txt && pytest`.

---

## 5. Roteiro de demonstração para o vídeo (≤ 10 min)

Sugestão de roteiro técnico, "apresentando para a equipe técnica de uma instituição":

1. **(0:00–1:00) Contexto.** O problema de recrutamento: currículos caóticos, salários sem
   comparabilidade, triagem manual. Objetivo da API.
2. **(1:00–2:30) Arquitetura.** Mostrar `docs/ARQUITETURA.md` e o pipeline híbrido.
   Destacar versionamento `/api/v1`, separação app/ai/api.
3. **(2:30–3:30) Documentação e autenticação.** Abrir `/docs`, fazer **Authorize**,
   mostrar o JWT emitido em `/auth/token`.
4. **(3:30–5:30) Serviço 1 — parse de currículo.** Enviar o currículo do engenheiro sênior;
   mostrar extração de skills, senioridade, formação, taxonomia, evidências e confiança.
   Enviar um texto "lixo" e mostrar `NO_MATCH/REVIEW`.
5. **(5:30–7:00) Serviço 2 — benchmark salarial.** Enviar um cargo com `offered_salary`;
   mostrar mediana, dispersão, **outliers detectados** e **gap vs. mercado**.
6. **(7:00–7:45) Serviço 3 — match.** Comparar currículo aderente vs. divergente.
7. **(7:45–8:45) Requisitos técnicos.** Mostrar um **422** (validação), o envelope de
   **erro padronizado**, os **logs JSON** com `request_id` no terminal, e os **testes**
   passando (`pytest`).
8. **(8:45–10:00) Visão de produto (Nexa Talent).** Como isso vira plataforma
   (seção 7) e o diferencial consultivo.

---

## 6. Mapa de rastreabilidade (critério UFG → arquivo)

| Critério | Arquivo(s) |
|---|---|
| 2+ serviços de IA | `app/api/v1/parse_resume.py`, `salary_benchmark.py`, `match.py` |
| Validação | `app/schemas.py` |
| Erros | `app/errors.py` |
| Logs | `app/logging_config.py`, middleware em `app/main.py` |
| Segurança/Auth | `app/security.py`, `app/api/deps.py`, `app/api/v1/auth.py` |
| Versionamento | `app/main.py` (prefixo `/api/v1`), `app/config.py` |
| Documentação | `/docs` automático, `README.md`, este roteiro |
| Roda em outra máquina | `requirements.txt`, `app/database.py` (seed automático) |
| Testes / cenários | `tests/` |

---

## 7. Evolução para produto — Nexa Talent

Esta API é a **Fase 1** do blueprint de inteligência de talentos. Caminho de evolução:

- **Fase 1 (atual):** taxonomia de cargos + parse + benchmark salarial + match,
  com dados de seed. Demonstra a tese de "infraestrutura semântica de talentos".
- **Fase 2:** ingestão real (ATS/LinkedIn), parsing de currículos não estruturados
  (PyMuPDF/pdfplumber/OCR), embeddings (pgvector/Qdrant) e fila de revisão humana.
- **Fase 3:** copiloto de recrutamento (RAG sobre a camada semântica), dashboards
  (Metabase/Superset), alertas de outlier salarial e governança (versionamento de
  taxonomia/prompt, drift).

**Posicionamento:** não se vende "um buscador de currículos", e sim uma **plataforma
semântica de inteligência de talentos** — transformar currículo, vaga e tabela salarial em
dados auditáveis, comparáveis e consultáveis por IA.

> Ver `docs/ARQUITETURA.md` para o desenho técnico completo e o esquema de dados-alvo.
