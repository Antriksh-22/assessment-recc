from fastapi.testclient import TestClient

from app.main import app


def test_finance_recommendations_include_catalog_items():
    client = TestClient(app)
    response = client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "Hiring graduate financial analysts; need numerical reasoning and finance knowledge."}]},
    )
    data = response.json()
    names = [r["name"] for r in data["recommendations"]]
    assert "Financial Accounting (New)" in names
    assert "Basic Statistics (New)" in names

