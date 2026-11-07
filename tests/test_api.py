import pytest
from fastapi.testclient import TestClient
from backend.config import Settings
from backend.main import create_app
from backend.storage import SQLiteStore
from tests.test_workflow import CONDITIONS


@pytest.fixture
def client(tmp_path):
    config = Settings(_env_file=None, sqlite_path=str(tmp_path / "demo.db"))
    return TestClient(create_app(config))


def session(client):
    response = client.post("/api/v1/sessions")
    assert response.status_code == 201
    return {"Authorization": "Bearer " + response.json()["token"]}


def test_auth_and_owner_isolation(client):
    assert client.get("/api/v1/runs").status_code == 401
    a, b = session(client), session(client)
    result = client.post("/api/v1/searches", headers=a, json={"conditions": CONDITIONS}).json()
    assert result["status"] == "completed"
    assert client.get("/api/v1/runs/" + result["run_id"], headers=b).status_code == 404
    assert client.get("/api/v1/runs", headers=b).json() == []


def test_question_followup_and_memory_precedence(client):
    headers = session(client)
    first = client.post("/api/v1/searches", headers=headers, json={"conditions": {"region": "서울특별시", "color": "갈색"}}).json()
    assert first["status"] == "awaiting_input"
    second = client.post("/api/v1/searches", headers=headers, json={"thread_id": first["thread_id"], "conditions": {"species": "dog", "start_date": "2025-01-01", "end_date": "2025-01-31"}}).json()
    assert second["status"] == "completed" and second["conditions"]["color"] == "갈색"
    client.put("/api/v1/memory", headers=headers, json={"confirmed": True, "conditions": {"species": "cat", "color": "검정"}})
    current = client.post("/api/v1/searches", headers=headers, json={"conditions": CONDITIONS, "use_memory": True}).json()
    assert current["conditions"]["species"] == "dog" and current["conditions"]["color"] == "갈색"
    assert client.put("/api/v1/memory", headers=headers, json={"confirmed": False, "conditions": {}}).status_code == 422


def test_saved_search_isolation_and_delete(client):
    a, b = session(client), session(client)
    saved = client.post("/api/v1/saved-searches", headers=a, json={"name": "우리 가족", "conditions": CONDITIONS}).json()
    assert len(client.get("/api/v1/saved-searches", headers=a).json()) == 1
    assert client.get("/api/v1/saved-searches", headers=b).json() == []
    assert client.delete("/api/v1/saved-searches/" + saved["id"], headers=b).status_code == 204
    assert len(client.get("/api/v1/saved-searches", headers=a).json()) == 1
    assert client.delete("/api/v1/saved-searches/" + saved["id"], headers=a).status_code == 204
    assert not client.get("/api/v1/saved-searches", headers=a).json()


def test_discord_config_and_consent_required(client):
    headers = session(client)
    saved = client.post("/api/v1/saved-searches", headers=headers, json={"name": "찾기", "conditions": CONDITIONS}).json()
    body = {"saved_search_id": saved["id"], "recipient": "123456789012345678", "consent": True}
    assert client.post("/api/v1/subscriptions", headers=headers, json=body).status_code == 503
    assert client.post("/api/v1/subscriptions", headers=headers, json={**body, "consent": False}).status_code == 422


async def test_sqlite_survives_reinitialization(tmp_path):
    path = str(tmp_path / "persist.db")
    await SQLiteStore(path).put("owner", "thread", "id", {"conditions": CONDITIONS})
    assert (await SQLiteStore(path).get("owner", "thread", "id"))["conditions"] == CONDITIONS
    assert await SQLiteStore(path).get("other", "thread", "id") is None


def test_live_mode_requires_explicit_credentials():
    with pytest.raises(ValueError):
        Settings(_env_file=None, app_mode="live", storage_backend="sqlite")
