import httpx
import pytest
from openai import AsyncOpenAI
from backend.tools import AnimalTools, Planner, ToolError
from backend.notifications import DiscordSender
from backend.storage import SupabaseStore
from tests.test_workflow import settings, CONDITIONS


def transport(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(handler)))


async def test_real_search_query_and_partial_coverage(monkeypatch):
    def handler(request):
        assert request.url.path.endswith("/abandonmentPublic_v2")
        assert request.url.params["bgnde"] == "20250101"
        assert request.url.params["upr_cd"] == "6110000"
        assert request.url.params["upkind"] == "417000"
        return httpx.Response(200, json={"response": {"header": {"resultCode": "00"}, "body": {"items": {"item": [{"desertionNo": "123", "happenDt": "20250101", "upKindCd": "417000", "kindNm": "푸들", "orgNm": "서울특별시"}]}, "totalCount": 100}}})
    transport(monkeypatch, handler)
    config = settings(max_search_pages=1)
    config.app_mode = "live"  # adapter test only, no real network or model
    candidates, coverage = await AnimalTools(config).search({**CONDITIONS, "region_code": "6110000"})
    assert len(candidates) == 1 and coverage["partial"] and coverage["total"] == 100


@pytest.mark.parametrize("response,code", [(httpx.Response(403), "auth"), (httpx.Response(429), "rate_limit"), (httpx.Response(200, text="<error>bad key</error>"), "malformed"), (httpx.Response(200, json={"response": {"header": {"resultCode": "00"}}}), "malformed")])
async def test_external_errors_are_not_empty_results(monkeypatch, response, code):
    transport(monkeypatch, lambda request: response)
    with pytest.raises(ToolError) as exc:
        await AnimalTools(settings()).api("abandonmentPublic_v2", {})
    assert exc.value.code == code


async def test_supabase_uses_custom_schema_and_owner_filters(monkeypatch):
    def handler(request):
        assert request.headers["Accept-Profile"] == "aio-03-p2-team1-demo"
        assert request.url.params["owner"] == "eq.owner-hash"
        assert request.url.params["kind"] == "eq.thread"
        return httpx.Response(200, json=[{"data": {"test": True}}])
    transport(monkeypatch, handler)
    store = SupabaseStore(settings(supabase_service_role_key="test-only-key"))
    assert await store.get("owner-hash", "thread", "thread-id") == {"test": True}


async def test_discord_adapter_creates_dm_then_message(monkeypatch):
    paths = []
    def handler(request):
        paths.append(request.url.path)
        assert request.headers["Authorization"] == "Bot fake-token"
        return httpx.Response(200, json={"id": "dm-channel" if len(paths) == 1 else "message-id"})
    transport(monkeypatch, handler)
    sender = DiscordSender(settings(discord_bot_token="fake-token", discord_allowed_user_ids="123456789012345678"))
    result = await sender.send("123456789012345678", "명시적으로 요청한 테스트 메시지")
    assert result["status"] == "accepted"
    assert paths == ["/api/v10/users/@me/channels", "/api/v10/channels/dm-channel/messages"]


def planner_transport(monkeypatch, handler):
    def client(**kwargs):
        return AsyncOpenAI(**kwargs, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr("backend.tools.AsyncOpenAI", client)
    config = settings(openai_api_key="sk-test-never-expose")
    config.app_mode = "live"
    return Planner(config)


@pytest.mark.parametrize("status,provider_code,expected", [
    (401, "invalid_api_key", "llm_auth"),
    (403, "permission_denied", "llm_permission"),
    (404, "model_not_found", "llm_model"),
    (429, "insufficient_quota", "llm_quota"),
    (429, "project_spend_limit_exceeded", "llm_quota"),
    (429, "rate_limit_exceeded", "llm_rate_limit"),
    (400, "invalid_request", "llm_request"),
    (503, "server_is_overloaded", "llm_upstream"),
])
async def test_planner_error_categories_do_not_expose_credentials(monkeypatch, caplog, status, provider_code, expected):
    def handler(request):
        return httpx.Response(status, headers={"x-request-id": "req-test-123"}, json={"error": {"message": "Incorrect key: sk-test-never-expose", "type": "api_error", "code": provider_code}})
    planner = planner_transport(monkeypatch, handler)
    with pytest.raises(ToolError) as error:
        await planner.plan({})
    assert error.value.code == expected
    assert "sk-test-never-expose" not in str(error.value)
    assert "sk-test-never-expose" not in caplog.text
    assert f"status={status}" in caplog.text
    assert "request_id=req-test-123" in caplog.text


@pytest.mark.parametrize("failure,expected", [(httpx.ReadTimeout, "llm_timeout"), (httpx.ConnectError, "llm_network")])
async def test_planner_connection_errors(monkeypatch, failure, expected):
    def handler(request):
        raise failure("test connection failure", request=request)
    planner = planner_transport(monkeypatch, handler)
    with pytest.raises(ToolError) as error:
        await planner.plan({})
    assert error.value.code == expected


@pytest.mark.parametrize("status,output,expected", [
    ("completed", '{"tools":["search","shelter"],"reason":"test"}', None),
    ("completed", "not json", "llm_response"),
    ("completed", '{"tools":"search","reason":"test"}', "llm_response"),
    ("completed", '{"tools":[{}],"reason":"test"}', "llm_response"),
    ("incomplete", "", "llm_response"),
])
async def test_planner_checks_completion_and_response_structure(monkeypatch, status, output, expected):
    def handler(request):
        return httpx.Response(200, json={"id": "resp-test", "object": "response", "status": status, "output": [{"type": "message", "id": "msg-test", "role": "assistant", "status": "completed", "content": [{"type": "output_text", "text": output, "annotations": []}]}]})
    planner = planner_transport(monkeypatch, handler)
    if expected:
        with pytest.raises(ToolError) as error:
            await planner.plan({})
        assert error.value.code == expected
    else:
        plan = await planner.plan({})
        assert plan["tools"] == ["search", "shelter"] and plan["tokens"] == 0
