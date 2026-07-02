from fastapi.testclient import TestClient

from app.main import app


def test_add_aws_docker_drop_rest():
    client = TestClient(app)
    response = client.post(
        "/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "Senior IC backend engineer. Core Java and Spring are day-one priorities; SQL is constant. Add AWS and Docker. Drop REST.",
                }
            ]
        },
    )
    names = [r["name"] for r in response.json()["recommendations"]]
    assert "Amazon Web Services (AWS) Development (New)" in names
    assert "Docker (New)" in names
    assert all("RESTful Web Services" not in name for name in names)


def test_remove_opq_final_management_trainee():
    client = TestClient(app)
    response = client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "Graduate management trainee final list: Verify G+ and Graduate Scenarios. Drop OPQ."}]},
    )
    data = response.json()
    names = [r["name"] for r in data["recommendations"]]
    assert names == ["SHL Verify Interactive G+", "Graduate Scenarios"]
    assert data["end_of_conversation"] is True

