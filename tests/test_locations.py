from copy import deepcopy
from uuid import uuid4

import httpx
import pytest

from backend.tools import AnimalTools, ToolError
from tests.test_adapters import transport
from tests.test_api import client, session
from tests.test_workflow import settings


LOCATION = {"address": "서울특별시 테스트 보호센터 주소", "coordinates": {"lat": 37.5, "lng": 127.0}, "source": "Kakao Local", "fetched_at": "2026-01-01T00:00:00+00:00"}


def stored_candidates(client):
    headers = session(client)
    owner = "user:" + client.get("/api/v1/auth/me", headers=headers).json()["user"]["id"]
    run_id = str(uuid4())
    result = {"run_id": run_id, "candidates": [{"id": str(i), "sample": False, "shelter_name": "테스트 보호센터", "shelter_address": LOCATION["address"]} for i in range(5)]}
    client.portal.call(client.app.state.store.put, owner, "run", run_id, result)
    return headers, owner, result


def test_location_for_fifth_candidate_is_cached_in_owners_run(client, monkeypatch):
    headers, owner, result = stored_candidates(client)
    calls = []

    async def location(self, candidate):
        calls.append(candidate["id"])
        return deepcopy(LOCATION)

    monkeypatch.setattr(AnimalTools, "location", location)
    path = f"/api/v1/runs/{result['run_id']}/candidates/4/location"
    assert client.get(path, headers=headers).json() == LOCATION
    assert client.get(path, headers=headers).json() == LOCATION
    assert calls == ["4"]
    saved = client.portal.call(client.app.state.store.get, owner, "run", result["run_id"])
    assert saved["candidates"][4]["location"] == LOCATION
    assert "location" not in saved["candidates"][0]


def test_location_endpoint_rejects_guests_other_owners_and_missing_candidates(client, monkeypatch):
    headers, _, result = stored_candidates(client)
    path = f"/api/v1/runs/{result['run_id']}/candidates/4/location"

    async def forbidden_call(self, candidate):
        pytest.fail("Unauthorized or missing records must not call Kakao")

    monkeypatch.setattr(AnimalTools, "location", forbidden_call)
    client.cookies.clear()
    assert client.get(path).status_code == 401
    other = session(client)
    assert client.get(path, headers=other).status_code == 404
    assert client.get(path.replace("/4/", "/missing/"), headers=headers).status_code == 404


def test_location_failure_can_be_retried_without_caching_error(client, monkeypatch):
    headers, owner, result = stored_candidates(client)
    attempts = 0

    async def location(self, candidate):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ToolError("location_timeout", "위치 조회 시간 초과", True)
        return deepcopy(LOCATION)

    monkeypatch.setattr(AnimalTools, "location", location)
    path = f"/api/v1/runs/{result['run_id']}/candidates/4/location"
    assert client.get(path, headers=headers).status_code == 502
    saved = client.portal.call(client.app.state.store.get, owner, "run", result["run_id"])
    assert "location" not in saved["candidates"][4]
    assert client.get(path, headers=headers).json() == LOCATION
    assert attempts == 2


@pytest.mark.parametrize("cached", [
    {**LOCATION, "address": "다른 주소"},
    {**LOCATION, "coordinates": {"lat": 100, "lng": 127}},
    {**LOCATION, "coordinates": {"lat": "37.5", "lng": "127"}},
])
def test_stale_or_invalid_coordinates_are_not_reused(client, monkeypatch, cached):
    headers, owner, result = stored_candidates(client)
    result["candidates"][4]["location"] = cached
    client.portal.call(client.app.state.store.put, owner, "run", result["run_id"], result)

    async def location(self, candidate):
        return deepcopy(LOCATION)

    monkeypatch.setattr(AnimalTools, "location", location)
    path = f"/api/v1/runs/{result['run_id']}/candidates/4/location"
    assert client.get(path, headers=headers).json() == LOCATION


async def test_kakao_geocodes_shelter_address_and_uses_correct_coordinate_order(monkeypatch):
    def handler(request):
        assert request.headers["Authorization"] == "KakaoAK test-rest-key"
        assert request.url.params["query"] == LOCATION["address"]
        return httpx.Response(200, json={"documents": [{"x": "127", "y": "37.5"}], "meta": {"total_count": 1}})

    transport(monkeypatch, handler)
    result = await AnimalTools(settings(kakao_rest_api_key="test-rest-key")).location({"shelter_address": LOCATION["address"], "shelter_name": "센터 / A"})
    assert result["coordinates"] == LOCATION["coordinates"]
    assert result["address"] == LOCATION["address"]
    assert "%2F" in result["map_url"]


@pytest.mark.parametrize("payload,expected", [
    ({"documents": []}, "address_not_found"),
    ({"documents": [{"x": "127", "y": "37.5"}], "meta": {"total_count": 2}}, "address_ambiguous"),
])
async def test_no_unique_address_does_not_make_up_coordinates(monkeypatch, payload, expected):
    transport(monkeypatch, lambda request: httpx.Response(200, json=payload))
    result = await AnimalTools(settings(kakao_rest_api_key="test-rest-key")).location({"shelter_address": "테스트 주소"})
    assert result["coordinates"] is None
    assert result["reason_code"] == expected


@pytest.mark.parametrize("status,expected", [(401, "location_auth"), (403, "location_auth"), (429, "location_rate_limit"), (500, "location_network")])
async def test_kakao_errors_do_not_expose_response_or_key(monkeypatch, status, expected):
    transport(monkeypatch, lambda request: httpx.Response(status, text="test-rest-key must not escape"))
    with pytest.raises(ToolError) as failure:
        await AnimalTools(settings(kakao_rest_api_key="test-rest-key")).location({"shelter_address": "테스트 주소"})
    assert failure.value.code == expected
    assert "test-rest-key" not in str(failure.value)


@pytest.mark.parametrize("document", [{"x": "NaN", "y": "37.5"}, {"x": "127", "y": "91"}, {"x": None, "y": "37.5"}, {}])
async def test_invalid_kakao_coordinates_are_not_shown(monkeypatch, document):
    transport(monkeypatch, lambda request: httpx.Response(200, json={"documents": [document]}))
    with pytest.raises(ToolError) as failure:
        await AnimalTools(settings(kakao_rest_api_key="test-rest-key")).location({"shelter_address": "테스트 주소"})
    assert failure.value.code == "location_response"


@pytest.mark.parametrize("candidate,configured,expected", [
    ({"sample": True, "shelter_address": "가상 주소"}, True, "sample"),
    ({"shelter_address": ""}, True, "address_missing"),
    ({"shelter_address": "테스트 주소"}, False, "not_configured"),
])
async def test_sample_missing_address_and_missing_key_skip_geocoding(monkeypatch, candidate, configured, expected):
    def handler(request):
        pytest.fail("No geocoding call should be made")

    transport(monkeypatch, handler)
    result = await AnimalTools(settings(kakao_rest_api_key="test-rest-key" if configured else "")).location(candidate)
    assert result["coordinates"] is None
    assert result["reason_code"] == expected
