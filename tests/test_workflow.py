from copy import deepcopy
from datetime import date
import pytest
from backend.config import Settings
from backend.graph import build_graph, initial_state
from backend.models import SearchRequest
from backend.tools import AnimalTools, Planner, ToolError

CONDITIONS = {"region": "서울특별시", "species": "dog", "start_date": "2025-01-01", "end_date": "2025-01-31", "color": "갈색"}


def settings(**kwargs):
    return Settings(_env_file=None, app_mode="local", **kwargs)


class FaultTools(AnimalTools):
    def __init__(self, config, fault="none"):
        super().__init__(config)
        self.fault, self.calls = fault, 0

    async def search(self, conditions):
        self.calls += 1
        if self.fault == "timeout" and self.calls == 1:
            raise ToolError("timeout", "고정 테스트의 일시적 타임아웃", True)
        if self.fault == "always_timeout":
            raise ToolError("timeout", "고정 테스트의 반복 타임아웃", True)
        if self.fault == "auth":
            raise ToolError("auth", "고정 테스트의 인증 실패", False)
        candidates, coverage = await super().search(conditions)
        if self.fault == "duplicate":
            candidates.append(deepcopy(candidates[0]))
        if self.fault == "mismatch":
            candidates.append({**candidates[0], "id": "WRONG", "species": "cat"})
        if self.fault == "empty":
            candidates = []
            coverage["total"] = 0
        return candidates, coverage


async def execute(fault="none", reflection=True, config=None, conditions=None, planner=None):
    config = config or settings()
    tools = FaultTools(config, fault)
    request = SearchRequest(conditions=conditions if conditions is not None else CONDITIONS, reflection=reflection)
    graph = build_graph(config, tools, planner or Planner(config))
    result = await graph.ainvoke(initial_state(request, request.conditions.model_dump(mode="json", exclude_none=True)), {"recursion_limit": 35})
    return result, tools


async def test_valid_search_ranking_and_provenance():
    result, tools = await execute()
    assert result["status"] == "completed"
    assert result["candidates"][0]["id"] == "SAMPLE-1"
    assert result["candidates"][0]["score"] == 100
    assert all(c["sample"] and c["fetched_at"] for c in result["candidates"])
    assert {t["node"] for t in result["traces"]} >= {"validate", "plan", "search", "verify", "shelter", "location"}


async def test_missing_conditions_never_call_search():
    result, tools = await execute(conditions={})
    assert result["status"] == "awaiting_input"
    assert len(result["questions"]) == 4
    assert tools.calls == 0


@pytest.mark.parametrize("fault", ["timeout", "duplicate", "mismatch"])
async def test_reflection_recovers_and_baseline_rejects(fault):
    baseline, _ = await execute(fault, False)
    reflected, _ = await execute(fault, True)
    assert baseline["status"] == "failed"
    assert reflected["status"] == "completed"
    assert reflected["iteration"] == 1
    assert len({c["id"] for c in reflected["candidates"]}) == len(reflected["candidates"])
    assert all(c["species"] == "dog" for c in reflected["candidates"])


async def test_repeat_limit_and_nonretryable_auth():
    result, tools = await execute("always_timeout")
    assert result["status"] == "failed" and result["iteration"] == 2
    assert tools.calls == 3
    result, tools = await execute("auth")
    assert result["status"] == "failed" and tools.calls == 1


async def test_empty_results_are_success_not_error():
    result, _ = await execute("empty")
    assert result["status"] == "completed" and not result["candidates"]


async def test_invalid_dates_do_not_execute():
    result, tools = await execute(conditions={**CONDITIONS, "start_date": "2025-02-01"})
    assert result["status"] == "awaiting_input" and tools.calls == 0


async def test_summary_preserves_conditions_and_bounds_messages():
    config = settings()
    request = SearchRequest(conditions=CONDITIONS)
    state = initial_state(request, CONDITIONS, {"recent_messages": ["메시지" * 200] * 20})
    graph = build_graph(config, FaultTools(config), Planner(config))
    result = await graph.ainvoke(state)
    assert result["summary"]["summarized"]
    assert result["summary"]["conditions"]["color"] == "갈색"
    assert sum(map(len, result["recent_messages"])) <= 3000


async def test_missing_tool_plan_can_be_corrected():
    class BadPlanner:
        async def plan(self, context):
            return {"tools": [], "reason": "고정 테스트의 잘못된 도구 선택", "tokens": 0}
    result, _ = await execute(planner=BadPlanner())
    assert result["status"] == "completed" and result["iteration"] == 1


def test_official_v2_field_normalization():
    tools = AnimalTools(settings())
    c = tools.normalize({"desertionNo": "123", "happenDt": "20250101", "upKindCd": "417000", "kindNm": "푸들", "colorCd": "흰색", "orgNm": "서울특별시", "careTel": "02-123-4567", "popfile1": "https://example.com/photo.jpg"})
    assert c["species"] == "dog" and c["found_date"] == "2025-01-01"
    assert c["shelter_phone"] == "02-123-4567"
