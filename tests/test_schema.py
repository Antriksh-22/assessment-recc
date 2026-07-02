from fastapi.testclient import TestClient

from app.main import app


def test_chat_schema():
    client = TestClient(app)
    response = client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "Hiring graduate financial analysts with numerical reasoning."}]},
    )
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"reply", "recommendations", "end_of_conversation"}
    assert isinstance(data["reply"], str)
    assert isinstance(data["recommendations"], list)
    assert isinstance(data["end_of_conversation"], bool)
    assert len(data["recommendations"]) <= 10

