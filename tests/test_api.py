import pytest
import httpx
from uuid import uuid4
from fakeredis import FakeAsyncRedis
from fastapi.testclient import TestClient
from backend.config import Settings
from backend.main import create_app
from backend.storage import SQLiteStore
from tests.test_workflow import CONDITIONS


@pytest.fixture
def client(tmp_path):
    config = Settings(_env_file=None, sqlite_path=str(tmp_path / "demo.db"))
    with TestClient(create_app(config, redis_client=FakeAsyncRedis(decode_responses=True))) as client:
        yield client


def session(client):
    # Each helper call represents a separate browser, not an account switch.
    client.cookies.clear()
    response = client.post("/api/v1/auth/register", json={"email": f"test-{uuid4().hex}@example.com", "password": "test-password-123", "name": "테스트"})
    assert response.status_code == 201
    return {"Cookie": "meet_again_session=" + response.cookies["meet_again_session"]}


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


@pytest.mark.parametrize("key_name", ["ANIMAL_API_KEY", "ANIMAL_API_SERVICE_KEY"])
def test_local_search_uses_configured_animal_api(tmp_path, monkeypatch, key_name):
    from tests.test_adapters import transport

    config = Settings(_env_file=None, sqlite_path=str(tmp_path / "api.db"), **{key_name: "encoded%2Bkey%3D"})
    requests = []

    def handler(request):
        requests.append(request)
        assert request.url.scheme == "https"
        assert request.url.params["serviceKey"] == "encoded+key="
        if request.url.path.endswith("/sido_v2"):
            items = [{"orgdownNm": "서울특별시", "orgCd": "6110000"}]
        else:
            assert request.url.path.endswith("/abandonmentPublic_v2")
            assert request.url.params["upr_cd"] == "6110000"
            assert request.url.params["upkind"] == "417000"
            assert request.url.params["bgnde"] == "20250101"
            assert request.url.params["endde"] == "20250131"
            items = [{"desertionNo": "REAL-123", "happenDt": "20250110", "upKindCd": "417000", "kindNm": "푸들", "orgNm": "서울특별시", "careNm": "보호센터", "careTel": "02-123-4567"}]
        return httpx.Response(200, json={"response": {"header": {"resultCode": "00"}, "body": {"items": {"item": items}, "totalCount": len(items)}}})

    transport(monkeypatch, handler)
    client = TestClient(create_app(config, redis_client=FakeAsyncRedis(decode_responses=True)))
    health = client.get("/api/v1/health").json()
    assert health["mode"] == "local" and health["animal_data_source"] == "api"
    assert not health["discord_configured"]
    assert client.get("/api/v1/regions").json()[0]["code"] == "6110000"
    result = client.post("/api/v1/searches", headers=session(client), json={"conditions": CONDITIONS, "include_location": False}).json()
    assert result["status"] == "completed"
    assert result["animal_data_source"] == "api" and result["tokens"] == 0
    assert result["candidates"][0]["id"] == "REAL-123"
    assert result["candidates"][0]["shelter_phone"] == "02-123-4567"
    assert not result["candidates"][0]["sample"]
    assert result["coverage"]["total"] == 1
    assert requests


def test_api_failure_does_not_fall_back_to_samples(tmp_path, monkeypatch):
    from tests.test_adapters import transport

    config = Settings(_env_file=None, sqlite_path=str(tmp_path / "failed.db"), animal_api_key="test-key")

    def handler(request):
        if request.url.path.endswith("/sido_v2"):
            return httpx.Response(200, json={"response": {"header": {"resultCode": "00"}, "body": {"items": {"item": [{"orgdownNm": "서울특별시", "orgCd": "6110000"}]}, "totalCount": 1}}})
        return httpx.Response(403)

    transport(monkeypatch, handler)
    client = TestClient(create_app(config, redis_client=FakeAsyncRedis(decode_responses=True)))
    result = client.post("/api/v1/searches", headers=session(client), json={"conditions": CONDITIONS}).json()
    assert result["status"] == "failed" and result["candidates"] == []
    assert result["errors"][0]["code"] == "auth"
    assert result["animal_data_source"] == "api"


def test_no_key_uses_samples_and_portal_http_url_is_upgraded():
    config = Settings(_env_file=None, animal_api_base_url="http://apis.data.go.kr/1543061/abandonmentPublicService_v2")
    assert config.animal_data_source == "sample"
    assert config.animal_api_base_url.startswith("https://")
