import httpx
import pytest
from backend.tools import AnimalTools, ToolError
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
