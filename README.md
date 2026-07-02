# SHL Assessment Recommender

Production-style FastAPI service for a stateless, catalog-only SHL assessment recommender.

The system helps recruiters and hiring managers choose relevant SHL assessments from the provided SHL catalog. It supports clarification, recommendation, refinement, comparison, and refusal for out-of-scope/legal/prompt-injection requests.

> Note: This is an API deployment, not a frontend website. Use `/docs` for browser-based testing or call `/chat` directly with a POST request.

---

## Public API Deployment

This project is deployed as a public FastAPI service.

### Base URL

```text
https://shl-assessment-recommender-kufk.onrender.com
