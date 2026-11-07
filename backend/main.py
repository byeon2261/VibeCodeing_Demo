import asyncio
import hashlib
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import FastAPI, APIRouter, Depends, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.config import get_settings
from backend.graph import build_graph, initial_state
from backend.models import SearchRequest, SavedSearch, SubscriptionRequest, MemoryUpdate, Conditions
from backend.notifications import DiscordSender, notify_matches
from backend.storage import SQLiteStore, SupabaseStore, StoreError, now
from backend.tools import AnimalTools, Planner, ToolError, today_seoul, ALIASES


def create_app(settings=None, store=None, tools=None, planner=None, sender=None):
    settings = settings or get_settings()
    store = store or (SupabaseStore(settings) if settings.storage_backend == "supabase" else SQLiteStore(settings.sqlite_path))
    tools = tools or AnimalTools(settings)
    planner = planner or Planner(settings)
    sender = sender or DiscordSender(settings)
    graph = build_graph(settings, tools, planner)
    locks = defaultdict(asyncio.Lock)
    rate_windows = defaultdict(deque)
    app = FastAPI(title="다시 만나 API", version="0.1.0")
    app.state.store, app.state.graph = store, graph
    app.add_middleware(CORSMiddleware, allow_origins=[s.strip() for s in settings.cors_origins.split(",")], allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Authorization", "Content-Type"])
    api = APIRouter(prefix="/api/v1")

    def rate_limit(key, maximum=20, seconds=60):
        current = time.monotonic()
        window = rate_windows[key]
        while window and current - window[0] > seconds:
            window.popleft()
        if len(window) >= maximum:
            raise HTTPException(429, "요청이 많습니다. 잠시 후 다시 시도해 주세요.")
        window.append(current)

    @app.exception_handler(StoreError)
    async def storage_error(request, exc):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(ToolError)
    async def tool_error(request, exc):
        return JSONResponse(status_code=502, content={"detail": str(exc), "code": exc.code})

    async def owner(authorization: str = Header(default="")):
        if not authorization.startswith("Bearer "):
            raise HTTPException(401, "데모 세션을 먼저 생성해 주세요.")
        token = authorization[7:]
        if not 40 <= len(token) <= 100:
            raise HTTPException(401, "유효하지 않은 데모 세션입니다.")
        digest = hashlib.sha256(token.encode()).hexdigest()
        if not await store.get(digest, "identity", "self"):
            raise HTTPException(401, "세션이 만료되었거나 유효하지 않습니다.")
        return digest

    @api.get("/health")
    async def health():
        return {"status": "ok", "mode": settings.app_mode, "storage": settings.storage_backend, "model": settings.openai_model, "discord_configured": bool(settings.discord_bot_token and settings.discord_allowed_user_ids), "browser_push": False, "sms": False, "scheduled_search": False}

    @api.post("/sessions", status_code=201)
    async def create_session(request: Request):
        rate_limit("session:" + (request.client.host if request.client else "unknown"), 10)
        token = secrets.token_urlsafe(32)
        digest = hashlib.sha256(token.encode()).hexdigest()
        await store.put(digest, "identity", "self", {"created_at": now()}, create_only=True)
        return {"token": token}

    @api.get("/regions")
    async def regions():
        return await tools.regions()

    @api.post("/searches")
    async def search(body: SearchRequest, identity=Depends(owner)):
        rate_limit("search:" + identity, 10)
        async with locks[identity]:
            previous = None
            if body.thread_id:
                previous = await store.get(identity, "thread", body.thread_id)
                if previous is None:
                    raise HTTPException(404, "대화를 찾을 수 없습니다.")
                if previous.get("profile_id") != body.profile_id:
                    raise HTTPException(409, "다른 동물 프로필은 새 대화에서 검색해 주세요.")
            memory = await store.get(identity, "memory", body.profile_id) if body.use_memory else None
            conditions = {**(memory or {}), **(previous or {}).get("conditions", {}), **body.conditions.model_dump(mode="json", exclude_none=True)}
            state = initial_state(body, conditions, previous)
            try:
                async with asyncio.timeout(settings.request_timeout_seconds):
                    result = await graph.ainvoke(state, {"recursion_limit": 35})
            except TimeoutError:
                result = {**state, "status": "failed", "errors": [{"code": "budget", "message": "전체 실행 시간 한도에 도달했습니다."}], "candidates": [], "elapsed_ms": settings.request_timeout_seconds * 1000}
            result.pop("started", None)
            result["mode"] = settings.app_mode
            result["profile_id"] = body.profile_id
            result["created_at"] = now()
            # Persist only validated conditions; invalid dates/region aren't committed to memory.
            await store.put(identity, "thread", result["thread_id"], {"conditions": result["conditions"], "summary": result.get("summary", {}), "recent_messages": result.get("recent_messages", []), "profile_id": body.profile_id})
            await store.put(identity, "run", result["run_id"], result)
            if result["status"] in ("completed", "partial") and settings.app_mode == "live":
                try:
                    async with asyncio.timeout(20):
                        await notify_matches(store, sender, identity, result["candidates"])
                except TimeoutError:
                    result["notification_warning"] = "알림 발송 시간 초과: 발송 이력을 확인해 주세요."
            return result

    @api.get("/runs")
    async def runs(identity=Depends(owner)):
        return await store.list(identity, "run")

    @api.get("/runs/{run_id}")
    async def get_run(run_id: str, identity=Depends(owner)):
        result = await store.get(identity, "run", run_id)
        if not result:
            raise HTTPException(404, "실행 이력이 없습니다.")
        return result

    @api.get("/saved-searches")
    async def saved_searches(identity=Depends(owner)):
        return await store.list(identity, "saved")

    @api.post("/saved-searches", status_code=201)
    async def save_search(body: SavedSearch, identity=Depends(owner)):
        c = body.conditions.model_dump(mode="json", exclude_none=True)
        # Reuse graph input validation without calling the LLM or search tools.
        if not all(c.get(x) for x in ("region", "species", "start_date", "end_date")):
            raise HTTPException(422, "지역·종류·기간을 모두 입력해 주세요.")
        if c["start_date"] > c["end_date"]:
            raise HTTPException(422, "검색 기간을 확인해 주세요.")
        if c["end_date"] > today_seoul().isoformat():
            raise HTTPException(422, "미래 기간은 저장할 수 없습니다.")
        c["region"] = ALIASES.get(c["region"], c["region"])
        if c["region"] not in {r["name"] for r in await tools.regions()}:
            raise HTTPException(422, "지원되는 시도 이름을 선택해 주세요.")
        key = str(uuid4())
        data = {"name": body.name, "conditions": c, "created_at": now()}
        await store.put(identity, "saved", key, data)
        return {"id": key, **data}

    @api.delete("/saved-searches/{key}", status_code=204)
    async def delete_saved(key: str, identity=Depends(owner)):
        for sub in await store.list(identity, "subscription"):
            if sub["saved_search_id"] == key:
                await store.delete(identity, "subscription", sub["id"])
        await store.delete(identity, "saved", key)

    @api.get("/memory/{profile_id}")
    async def memory(profile_id: str, identity=Depends(owner)):
        return await store.get(identity, "memory", profile_id) or {}

    @api.put("/memory")
    async def save_memory(body: MemoryUpdate, identity=Depends(owner)):
        # Dates are request-specific. Store confirmed animal features only.
        data = body.conditions.model_dump(mode="json", exclude_none=True, include={"species", "breed", "color", "features"})
        await store.put(identity, "memory", body.profile_id, data)
        return data

    @api.delete("/memory/{profile_id}", status_code=204)
    async def delete_memory(profile_id: str, identity=Depends(owner)):
        await store.delete(identity, "memory", profile_id)

    @api.post("/subscriptions", status_code=201)
    async def subscribe(body: SubscriptionRequest, identity=Depends(owner)):
        rate_limit("subscribe:" + identity, 5)
        if not body.consent:
            raise HTTPException(422, "수신 동의가 필요합니다.")
        if not await store.get(identity, "saved", body.saved_search_id):
            raise HTTPException(404, "저장한 검색이 없습니다.")
        if not sender.allowed(body.recipient):
            raise HTTPException(503, "Discord Bot과 동의받은 수신자 허용 목록을 서버에 설정해 주세요.")
        key = str(uuid4())
        data = {**body.model_dump(), "active": True, "created_at": now()}
        for sub in await store.list(identity, "subscription"):
            if sub["saved_search_id"] == body.saved_search_id and sub["recipient"] == body.recipient and sub.get("active"):
                return {"id": sub["id"], "active": True, "channel": body.channel}
        await store.put(identity, "subscription", key, data)
        return {"id": key, "active": True, "channel": body.channel}

    @api.get("/subscriptions")
    async def subscriptions(identity=Depends(owner)):
        return [{k: v for k, v in s.items() if k != "recipient"} for s in await store.list(identity, "subscription")]

    @api.delete("/subscriptions/{key}", status_code=204)
    async def unsubscribe(key: str, identity=Depends(owner)):
        await store.delete(identity, "subscription", key)

    @api.get("/notifications")
    async def notifications(identity=Depends(owner)):
        return await store.list(identity, "notification")

    app.include_router(api)
    return app


app = create_app()
