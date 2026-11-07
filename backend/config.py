from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_mode: Literal["local", "live"] = "local"
    storage_backend: Literal["sqlite", "supabase"] = "sqlite"
    sqlite_path: str = ".data/meet-again.db"
    supabase_url: str = "https://yaywavgjaquftvekuvsb.supabase.co"
    supabase_schema: str = "aio-03-p2-team1-demo"
    supabase_service_role_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-6-luna"
    animal_api_key: str = ""
    animal_api_base_url: str = "https://apis.data.go.kr/1543061/abandonmentPublicService_v2"
    kakao_rest_api_key: str = ""
    discord_bot_token: str = ""
    discord_allowed_user_ids: str = ""
    cors_origins: str = "http://localhost:5173"
    max_search_pages: int = Field(default=3, ge=1, le=10)
    max_reflections: int = Field(default=2, ge=0, le=3)
    max_tool_calls: int = Field(default=30, ge=10, le=60)
    request_timeout_seconds: int = Field(default=60, ge=10, le=120)

    @model_validator(mode="after")
    def deployment_checks(self):
        if self.app_mode == "live":
            missing = [name for name in ("openai_api_key", "animal_api_key") if not getattr(self, name)]
            if self.storage_backend != "supabase":
                missing.append("STORAGE_BACKEND=supabase")
            if missing:
                raise ValueError("실제 연동 모드 설정 누락: " + ", ".join(missing))
        if self.storage_backend == "supabase" and not self.supabase_service_role_key:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY 설정이 필요합니다.")
        return self


@lru_cache
def get_settings():
    return Settings()
