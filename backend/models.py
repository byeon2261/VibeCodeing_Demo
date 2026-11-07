from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Conditions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    region: str | None = Field(default=None, max_length=30)
    region_code: str | None = Field(default=None, pattern=r"^\d{7}$")
    district_code: str | None = Field(default=None, pattern=r"^\d{7}$")
    species: Literal["dog", "cat", "other", "all"] | None = None
    start_date: date | None = None
    end_date: date | None = None
    breed: str | None = Field(default=None, max_length=80)
    color: str | None = Field(default=None, max_length=80)
    features: str | None = Field(default=None, max_length=500)


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conditions: Conditions = Field(default_factory=Conditions)
    message: str = Field(default="", max_length=2000)
    thread_id: str | None = Field(default=None, pattern=r"^[a-f0-9-]{36}$")
    profile_id: str = Field(default="default", pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    use_memory: bool = False
    reflection: bool = True
    include_location: bool = True


class Candidate(BaseModel):
    id: str
    notice_no: str = ""
    species: str
    breed: str = ""
    color: str = ""
    features: str = ""
    found_date: str
    found_place: str = ""
    region: str = ""
    status: str = ""
    shelter_name: str = ""
    shelter_phone: str = ""
    shelter_address: str = ""
    image_url: str = ""
    source_url: str = "https://www.animal.go.kr/"
    fetched_at: str
    score: int = 0
    matches: list[str] = Field(default_factory=list)
    mismatches: list[str] = Field(default_factory=list)
    unknown: list[str] = Field(default_factory=list)
    location: dict | None = None
    sample: bool = False


class SavedSearch(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    conditions: Conditions


class MemoryUpdate(BaseModel):
    profile_id: str = Field(default="default", pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    confirmed: bool
    conditions: Conditions

    @model_validator(mode="after")
    def confirmed_only(self):
        if not self.confirmed:
            raise ValueError("확인한 특징만 저장할 수 있습니다.")
        return self


class SubscriptionRequest(BaseModel):
    saved_search_id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    channel: Literal["discord"] = "discord"
    recipient: str = Field(pattern=r"^\d{17,20}$")
    consent: bool
