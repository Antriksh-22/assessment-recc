# SHL Assessment Recommender

Production-style FastAPI service for a **stateless, catalog-only SHL assessment recommender**.

The system recommends SHL assessments from the provided catalog JSON. It supports clarification, recommendation, refinement, comparison, and refusal for out-of-scope, legal, or prompt-injection requests.

> This is an API deployment, not a frontend website. Use `/docs` for browser-based testing or call `/chat` directly.

---

## Public API

**Base URL**

```text
https://shl-assessment-recommender-kufk.onrender.com
```

**Interactive API docs**

```text
https://shl-assessment-recommender-kufk.onrender.com/docs
```

Opening the base URL returns API info. The evaluator should call:

```text
GET  /health
POST /chat
```

---

## Endpoints

### Health

```http
GET /health
```

Example:

```bash
curl https://shl-assessment-recommender-kufk.onrender.com/health
```

Expected:

```json
{"status":"ok"}
```

### Chat

```http
POST /chat
```

Example:

```bash
curl -X POST https://shl-assessment-recommender-kufk.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"We run a graduate management trainee scheme. Need cognitive, personality, and situational judgement."}]}'
```

Expected response shape:

```json
{
  "reply": "string",
  "recommendations": [
    {
      "name": "string",
      "url": "string",
      "test_type": "string"
    }
  ],
  "end_of_conversation": false
}
```

Recommendations are always validated against the SHL catalog.

---

## Demo Test

Use this in `/docs` → `POST /chat` → **Try it out**:

```json
{
  "messages": [
    {
      "role": "user",
      "content": "We run a graduate management trainee scheme. Need cognitive, personality, and situational judgement."
    }
  ]
}
```

Expected recommendations:

```text
SHL Verify Interactive G+
Occupational Personality Questionnaire OPQ32r
Graduate Scenarios
```

Additional quick checks:

```json
{"messages":[{"role":"user","content":"I need an assessment."}]}
```

Expected: asks clarification, no recommendations.

```json
{"messages":[{"role":"user","content":"Senior IC backend engineer. Core Java and Spring are day-one priorities; SQL is constant. Add AWS and Docker. Drop REST."}]}
```

Expected: includes Java, Spring, SQL, AWS, Docker, Verify G+, OPQ32r; excludes RESTful Web Services.

```json
{"messages":[{"role":"user","content":"Are we legally required under HIPAA to test all staff who touch patient records?"}]}
```

Expected: refuses legal advice, no recommendations.

---

## Local Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

If activation is blocked:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\venv\Scripts\Activate.ps1
```

Test locally:

```bash
curl http://localhost:8000/health
```

---

## Data

Expected files:

```text
data/shl_catalog.json
data/traces/C1.md through C10.md
```

This submission includes the provided SHL catalog.

---

## Environment Variables

```env
USE_LLM=false
ENABLE_KG=true
SARVAM_API_KEY=
SARVAM_BASE_URL=https://api.sarvam.ai/v1/chat/completions
SARVAM_MODEL=sarvam-30b
CATALOG_PATH=data/shl_catalog.json
TOP_K_RETRIEVAL=30
TOP_K_FINAL=10
```

Sarvam AI is optional and only polishes reply text. Recommendation selection remains deterministic and catalog-backed.

`ENABLE_KG=true` enables a lightweight in-memory knowledge graph. No Neo4j or external graph database is used.

---

## Tests

```bash
pytest
python eval/run_eval.py
python eval/behavior_tests.py
```

Current local test status:

```text
17 passed
```

---

## Design Summary

```text
Hybrid retrieval
+ risk-aware reranking
+ lightweight catalog knowledge graph
+ strict catalog validation
+ optional Sarvam AI reply polishing
```

The service is stateless. Every `/chat` call rebuilds context from the supplied message history and stores no per-conversation state.
