# SHL Assessment Recommender

Production-style FastAPI service for a stateless, catalog-only SHL assessment recommender.

## Local Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

On Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Data Placement

The project expects:

- `data/shl_catalog.json`: SHL catalog JSON. This submission includes the provided catalog.
- `data/traces/C1.md` through `C10.md`: public conversation traces.

Set `CATALOG_PATH` if the catalog is stored elsewhere.

## API

Health:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Chat:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hiring a senior Java backend engineer with Spring and SQL"}]}'
```

Response schema is always:

```json
{
  "reply": "string",
  "recommendations": [],
  "end_of_conversation": false
}
```

Recommendations contain only catalog-backed `name`, `url`, and `test_type` fields.

## Environment Variables

- `USE_LLM`: `true` or `false`. The app works with `false`.
- `ENABLE_KG`: `true` or `false`. Defaults to `true`; the lightweight in-memory knowledge graph is optional.
- `SARVAM_API_KEY`: Sarvam key.
- `SARVAM_BASE_URL`: default `https://api.sarvam.ai/v1/chat/completions`.
- `SARVAM_MODEL`: default `sarvam-30b`.
- `CATALOG_PATH`: default `data/shl_catalog.json`.
- `TOP_K_RETRIEVAL`: default `30`.
- `TOP_K_FINAL`: default `10`.

Sarvam is used only to polish reply text. Recommendation selection remains deterministic. The optional knowledge graph uses plain in-memory Python structures for small reranking/explanation boosts; no Neo4j or external graph database is required.

## Tests and Evaluation

```bash
pytest
python eval/run_eval.py
python eval/behavior_tests.py
```

The evaluator checks schema compliance, catalog URL validation, guardrails, refinement, comparison, and Recall@10 against the trace-derived expected shortlists.

## Render Deployment

1. Push this repository to GitHub.
2. Create a Render web service from the repo.
3. Use the included `render.yaml` or Docker runtime.
4. Set environment variables:
   - `USE_LLM=true` if using Sarvam polishing.
   - `ENABLE_KG=true`
   - `SARVAM_API_KEY`
   - `SARVAM_BASE_URL=https://api.sarvam.ai/v1/chat/completions`
   - `SARVAM_MODEL=sarvam-30b`
   - `CATALOG_PATH=data/shl_catalog.json`
   - `TOP_K_RETRIEVAL=30`
   - `TOP_K_FINAL=10`

Render start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Notes

The service is stateless: each `/chat` request rebuilds context from the supplied message history. It never stores per-conversation state and validates every returned recommendation against the catalog.
