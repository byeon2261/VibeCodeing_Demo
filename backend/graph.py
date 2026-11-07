import asyncio
import time
from typing import TypedDict
from uuid import uuid4
from langgraph.graph import StateGraph, START, END
from backend.models import Conditions
from backend.tools import ALIASES, ToolError, today_seoul
from backend.storage import now


class SearchState(TypedDict, total=False):
    run_id: str
    thread_id: str
    conditions: dict
    message: str
    summary: dict
    recent_messages: list
    include_location: bool
    reflection: bool
    status: str
    questions: list[str]
    plan: list[str]
    candidates: list[dict]
    coverage: dict
    traces: list[dict]
    errors: list[dict]
    iteration: int
    tool_calls: int
    tokens: int
    started: float
    elapsed_ms: int
    retry: str
    verified: bool


def trace(state, node, detail):
    return state.get("traces", []) + [{"node": node, "detail": detail, "at": now()}]


def rank_candidates(candidates, conditions):
    result = []
    for candidate in candidates:
        c = {**candidate, "matches": [], "mismatches": [], "unknown": []}
        earned, possible = 0, 0
        for field, label, weight in (("breed", "품종", 3), ("color", "털색", 2), ("features", "특징", 2)):
            requested = conditions.get(field)
            if not requested:
                continue
            possible += weight
            actual = c.get(field, "")
            if not actual:
                c["unknown"].append(label + " 정보 없음")
            elif requested.replace(" ", "").casefold() in actual.replace(" ", "").casefold():
                earned += weight
                c["matches"].append(label + ": " + actual)
            else:
                c["mismatches"].append(label + ": " + actual)
        c["score"] = round(earned / possible * 100) if possible else 0
        result.append(c)
    return sorted(result, key=lambda c: (-c["score"], c["id"]))


def candidate_errors(candidates, conditions):
    errors, seen = [], set()
    for c in candidates:
        if c["id"] in seen:
            errors.append({"code": "duplicate", "message": "중복 공고를 제거해야 합니다.", "retryable": True})
        seen.add(c["id"])
        if conditions["species"] != "all" and c["species"] != conditions["species"]:
            errors.append({"code": "condition", "message": "동물 종류가 다른 후보를 제외해야 합니다.", "retryable": True})
        if not conditions["start_date"] <= c["found_date"] <= conditions["end_date"]:
            errors.append({"code": "condition", "message": "검색 기간 밖의 후보를 제외해야 합니다.", "retryable": True})
        # API orgNm is human-readable; require the selected province name.
        if conditions["region"] not in c.get("region", ""):
            errors.append({"code": "condition", "message": "선택 지역과 다른 후보를 제외해야 합니다.", "retryable": True})
    return errors


def build_graph(settings, tools, planner):
    async def validate(state):
        c = Conditions.model_validate(state["conditions"]).model_dump(mode="json", exclude_none=True)
        if c.get("region"):
            c["region"] = ALIASES.get(c["region"], c["region"])
        questions = [label + "을(를) 입력해 주세요." for key, label in (("region", "검색 지역"), ("species", "동물 종류"), ("start_date", "검색 시작일"), ("end_date", "검색 종료일")) if not c.get(key)]
        if c.get("start_date") and c.get("end_date"):
            if c["start_date"] > c["end_date"]:
                questions.append("시작일이 종료일보다 늦습니다. 기간을 수정해 주세요.")
            if c["end_date"] > today_seoul().isoformat():
                questions.append("미래 날짜 대신 오늘 이전의 기간을 선택해 주세요.")
        if not questions:
            try:
                regions = await tools.regions()
                match = next((r for r in regions if r["name"] == c["region"]), None)
                if not match:
                    questions.append("지원되는 시도 이름을 선택해 주세요.")
                else:
                    c["region_code"] = match["code"]
                    if c.get("district_code"):
                        questions.append("현재 데모는 시도 단위 검색을 지원합니다. 시군구 코드를 제거해 주세요.")
            except ToolError as exc:
                return {"status": "failed", "errors": [{"code": exc.code, "message": str(exc), "retryable": False}], "traces": trace(state, "validate", str(exc))}
        return {"conditions": c, "questions": questions, "status": "awaiting_input" if questions else "running", "traces": trace(state, "validate", "필수 조건 확인" if not questions else "추가 입력 필요")}

    async def context(state):
        messages = state.get("recent_messages", []) + ([state["message"]] if state.get("message") else [])
        # Structured summary is the source of truth; preserve conditions without LLM paraphrasing.
        summarized = len(messages) > 6 or sum(map(len, messages)) > 3000
        retained = messages[-6:]
        while retained and sum(map(len, retained)) > 3000:
            retained.pop(0)
        summary = {"conditions": state["conditions"], "unresolved": state.get("questions", []), "previous": state.get("summary", {}).get("conditions", {}), "summarized": summarized}
        return {"summary": summary, "recent_messages": retained, "traces": trace(state, "context", f"확정 조건 보존 · 최근 메시지 {len(retained)}개 · 요약 {summarized}")}

    async def plan(state):
        try:
            # Deliberately omit free text/contacts; structured conditions bound planner input.
            p = await planner.plan({"conditions": state["conditions"], "include_location": state["include_location"], "summary": state["summary"]})
            selected = list(dict.fromkeys(x for x in p["tools"] if x in ("search", "shelter", "location")))
            if not state["include_location"]:
                selected = [x for x in selected if x != "location"]
            return {"plan": selected, "tokens": state.get("tokens", 0) + p.get("tokens", 0), "traces": trace(state, "plan", p["reason"][:300])}
        except ToolError as exc:
            return {"status": "failed", "errors": [{"code": exc.code, "message": str(exc), "retryable": False}], "traces": trace(state, "plan", str(exc))}

    async def execute(state):
        selected = state.get("plan", [])
        if state["tool_calls"] + settings.max_search_pages > settings.max_tool_calls:
            return {"errors": [{"code": "budget", "message": "도구 호출 예산에 도달했습니다.", "retryable": False}]}
        if "search" not in selected:
            return {"errors": [{"code": "missing_tool", "message": "검색 도구가 계획에서 누락되었습니다.", "retryable": True}], "traces": trace(state, "search", "검색 도구 누락 감지")}
        try:
            candidates, coverage = await tools.search(state["conditions"])
            return {"candidates": candidates, "coverage": coverage, "errors": [], "tool_calls": state["tool_calls"] + coverage["pages"], "traces": trace(state, "search", f"{coverage['pages']}페이지 · {len(candidates)}건 수집")}
        except ToolError as exc:
            return {"errors": [{"code": exc.code, "message": str(exc), "retryable": exc.retryable}], "tool_calls": state["tool_calls"] + 1, "traces": trace(state, "search", str(exc))}

    async def verify(state):
        errors = list(state.get("errors", []))
        if not errors:
            errors = candidate_errors(state.get("candidates", []), state["conditions"])
        if state.get("candidates") and "shelter" not in state.get("plan", []):
            errors.append({"code": "missing_shelter", "message": "보호센터 확인 도구가 누락되었습니다.", "retryable": True})
        if state.get("candidates") and state["include_location"] and "location" not in state.get("plan", []):
            errors.append({"code": "missing_location", "message": "위치 확인 도구가 누락되었습니다.", "retryable": True})
        return {"errors": errors, "verified": not errors, "traces": trace(state, "verify", "검증 통과" if not errors else "; ".join(dict.fromkeys(e["message"] for e in errors)))}

    async def reflect(state):
        errors = state["errors"]
        can_retry = all(e["retryable"] for e in errors) and state["iteration"] < settings.max_reflections
        if not can_retry:
            return {"status": "failed", "retry": "stop", "traces": trace(state, "reflect", "복구 불가 또는 반복 한도 도달")}
        codes = {e["code"] for e in errors}
        iteration = state["iteration"] + 1
        selected = list(dict.fromkeys(state.get("plan", []) + ["search", "shelter"] + (["location"] if state["include_location"] else [])))
        if codes <= {"condition", "duplicate", "missing_shelter", "missing_location"}:
            valid = {}
            for c in state.get("candidates", []):
                if not candidate_errors([c], state["conditions"]):
                    valid[c["id"]] = c
            return {"plan": selected, "candidates": list(valid.values()), "errors": [], "iteration": iteration, "retry": "verify", "traces": trace(state, "reflect", "조건 위반·중복 제거 및 필수 도구 보완 → 재검증")}
        await asyncio.sleep(min(0.2 * (2 ** (iteration - 1)), 1))
        return {"plan": selected, "errors": [], "iteration": iteration, "retry": "execute", "traces": trace(state, "reflect", "도구 계획 보완 또는 일시적 오류 백오프 → 재실행")}

    async def enrich(state):
        ranked = rank_candidates(state.get("candidates", []), state["conditions"])[:10]
        traces, calls, warnings = state["traces"], state["tool_calls"], []
        for c in ranked[:3]:
            if calls + 2 > settings.max_tool_calls:
                warnings.append({"code": "budget", "message": "일부 상세 도구는 호출 예산 때문에 생략했습니다.", "retryable": False})
                break
            if "shelter" in state["plan"]:
                c.update(await tools.shelter(c))
                calls += 1
            if "location" in state["plan"]:
                try:
                    c["location"] = await tools.location(c)
                except ToolError as exc:
                    c["location"] = {"coordinates": None, "address": c["shelter_address"], "reason": str(exc)}
                    warnings.append({"code": exc.code, "message": str(exc), "retryable": False})
                calls += 1
        traces += [{"node": "shelter", "detail": "상위 3개 후보의 원본 보호센터 정보 확인", "at": now()}]
        if "location" in state["plan"]:
            traces += [{"node": "location", "detail": "상위 3개 후보의 보호센터 주소 확인", "at": now()}]
        partial = state.get("coverage", {}).get("partial", False) or bool(warnings)
        return {"candidates": ranked, "status": "partial" if partial else "completed", "errors": warnings, "tool_calls": calls, "traces": traces}

    async def finish(state):
        failed = state.get("errors") and not state.get("verified")
        return {"status": "failed" if failed else state.get("status", "failed"), "candidates": [] if failed else state.get("candidates", []), "elapsed_ms": round((time.monotonic() - state["started"]) * 1000), "traces": trace(state, "finish", "실행 종료 · 샘플" if settings.app_mode == "local" else "실행 종료 · 실제 API")}

    graph = StateGraph(SearchState)
    for name, node in (("validate", validate), ("context", context), ("plan", plan), ("execute", execute), ("verify", verify), ("reflect", reflect), ("enrich", enrich), ("finish", finish)):
        graph.add_node(name, node)
    graph.add_edge(START, "validate")
    graph.add_conditional_edges("validate", lambda s: "finish" if s["status"] in ("failed", "awaiting_input") else "context")
    graph.add_edge("context", "plan")
    graph.add_conditional_edges("plan", lambda s: "finish" if s["status"] == "failed" else "execute")
    graph.add_edge("execute", "verify")
    graph.add_conditional_edges("verify", lambda s: "enrich" if not s["errors"] else "reflect" if s["reflection"] else "finish")
    graph.add_conditional_edges("reflect", lambda s: {"stop": "finish", "verify": "verify", "execute": "execute"}[s["retry"]])
    graph.add_edge("enrich", "finish")
    graph.add_edge("finish", END)
    return graph.compile()


def initial_state(request, conditions, previous=None):
    previous = previous or {}
    return {"run_id": str(uuid4()), "thread_id": request.thread_id or str(uuid4()), "conditions": conditions, "message": request.message, "summary": previous.get("summary", {}), "recent_messages": previous.get("recent_messages", []), "include_location": request.include_location, "reflection": request.reflection, "status": "running", "questions": [], "plan": [], "candidates": [], "coverage": {}, "traces": [], "errors": [], "iteration": 0, "tool_calls": 0, "tokens": 0, "verified": False, "started": time.monotonic()}
