"""Password accounts in the document store; expiring, revocable sessions in Redis."""
import asyncio
import hashlib
import json
import secrets
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator
from pwdlib import PasswordHash
from redis.asyncio import Redis
from redis.exceptions import RedisError

from backend.storage import now

COOKIE_NAME = "meet_again_session"
COOKIE_PATH = "/api/v1"
PASSWORDS = PasswordHash.recommended()
DUMMY_HASH = PASSWORDS.hash(secrets.token_urlsafe(32))


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr = Field(max_length=254)
    password: SecretStr

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value):
        return str(value).casefold()

    @field_validator("password")
    @classmethod
    def password_length(cls, value):
        if not 10 <= len(value.get_secret_value()) <= 128:
            raise ValueError("비밀번호는 10~128자로 입력해 주세요.")
        return value


class Registration(Credentials):
    name: str = Field(min_length=1, max_length=40)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("이름을 입력해 주세요.")
        return value


class AuthService:
    def __init__(self, settings, store, redis_client=None):
        self.settings, self.store = settings, store
        self.redis = redis_client if redis_client is not None else Redis.from_url(
            settings.redis_url, decode_responses=True, socket_connect_timeout=3,
            socket_timeout=3, protocol=2,
        )
        self.owns_redis = redis_client is None
        self.hash_slots = asyncio.Semaphore(2)

    @staticmethod
    def account_key(email):
        return "account:" + hashlib.sha256(email.encode()).hexdigest()

    @staticmethod
    def session_key(token):
        return "meet-again:auth:session:" + hashlib.sha256(token.encode()).hexdigest()

    async def limited(self, bucket, maximum, seconds):
        key = "meet-again:auth:limit:" + hashlib.sha256(bucket.encode()).hexdigest()
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, seconds, nx=True)
                count, _ = await pipe.execute()
        except RedisError as exc:
            raise HTTPException(503, "로그인 서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.") from exc
        if count > maximum:
            raise HTTPException(429, "로그인 요청이 많습니다. 잠시 후 다시 시도해 주세요.", headers={"Retry-After": str(seconds)})

    async def current(self, request: Request):
        token = request.cookies.get(COOKIE_NAME, "")
        if not 40 <= len(token) <= 100:
            raise HTTPException(401, "로그인이 필요합니다.")
        try:
            raw = await self.redis.get(self.session_key(token))
        except RedisError as exc:
            raise HTTPException(503, "로그인 서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.") from exc
        if not raw:
            raise HTTPException(401, "로그인이 만료되었습니다. 다시 로그인해 주세요.")
        try:
            user = json.loads(raw)
            if not isinstance(user, dict) or not all(isinstance(user.get(k), str) for k in ("id", "email", "name")):
                raise ValueError("invalid session")
            return {k: user[k] for k in ("id", "email", "name")}
        except (ValueError, TypeError) as exc:
            raise HTTPException(401, "유효하지 않은 로그인입니다. 다시 로그인해 주세요.") from exc

    async def issue(self, request, response, user):
        token = secrets.token_urlsafe(32)
        try:
            # Rotate the current browser's session on both login and signup.
            async with self.redis.pipeline(transaction=True) as pipe:
                old = request.cookies.get(COOKIE_NAME)
                if old:
                    pipe.delete(self.session_key(old))
                pipe.set(self.session_key(token), json.dumps(user), ex=self.settings.auth_session_ttl_seconds)
                await pipe.execute()
        except RedisError as exc:
            raise HTTPException(503, "로그인 서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.") from exc
        response.set_cookie(COOKIE_NAME, token, max_age=self.settings.auth_session_ttl_seconds,
                            httponly=True, secure=self.settings.secure_auth_cookie,
                            samesite=self.settings.auth_cookie_samesite, path=COOKIE_PATH)

    async def close(self):
        if self.owns_redis:
            await self.redis.aclose()


def auth_router(auth):
    router = APIRouter(prefix="/auth", tags=["인증"])

    @router.post("/register", status_code=201)
    async def register(body: Registration, request: Request):
        ip = request.client.host if request.client else "unknown"
        await auth.limited("register:" + ip, 5, 3600)
        async with auth.hash_slots:
            password_hash = await asyncio.to_thread(PASSWORDS.hash, body.password.get_secret_value())
        user = {"id": str(uuid4()), "email": str(body.email), "name": body.name}
        record = {**user, "password_hash": password_hash, "created_at": now()}
        created = await auth.store.put(auth.account_key(user["email"]), "identity", "account", record, create_only=True)
        if not created:
            raise HTTPException(409, "이미 가입된 이메일입니다. 로그인해 주세요.")
        # A failed Redis connection after account creation still allows a later login.
        response = Response(content=json.dumps({"user": user}), media_type="application/json", status_code=201)
        await auth.issue(request, response, user)
        return response

    @router.post("/login")
    async def login(body: Credentials, request: Request):
        ip = request.client.host if request.client else "unknown"
        email = str(body.email)
        await auth.limited("login-ip:" + ip, 30, 600)
        await auth.limited("login-email:" + email, 10, 600)
        account = await auth.store.get(auth.account_key(email), "identity", "account")
        async with auth.hash_slots:
            valid = await asyncio.to_thread(PASSWORDS.verify, body.password.get_secret_value(), account["password_hash"] if account else DUMMY_HASH)
        if not account or not valid:
            raise HTTPException(401, "이메일 또는 비밀번호를 확인해 주세요.")
        user = {k: account[k] for k in ("id", "email", "name")}
        response = Response(content=json.dumps({"user": user}), media_type="application/json")
        await auth.issue(request, response, user)
        return response

    @router.get("/me")
    async def me(user=Depends(auth.current)):
        return {"user": user}

    @router.post("/logout", status_code=204)
    async def logout(request: Request):
        token = request.cookies.get(COOKIE_NAME)
        if token:
            try:
                await auth.redis.delete(auth.session_key(token))
            except RedisError as exc:
                raise HTTPException(503, "로그아웃을 완료하지 못했습니다. 잠시 후 다시 시도해 주세요.") from exc
        response = Response(status_code=204)
        response.delete_cookie(COOKIE_NAME, path=COOKIE_PATH, httponly=True,
                               secure=auth.settings.secure_auth_cookie, samesite=auth.settings.auth_cookie_samesite)
        return response

    return router
