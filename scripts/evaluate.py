"""Deterministic fault-injection experiment, not real-world animal search accuracy."""
import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone
from tests.test_workflow import execute


async def main():
    rows = []
    for reflection in (False, True):
        for fault in ("none", "timeout", "duplicate", "mismatch", "empty", "auth", "always_timeout"):
            result, _ = await execute(fault, reflection)
            expected = "failed" if fault in ("auth", "always_timeout") else "completed"
            rows.append({"reflection": reflection, "scenario": fault, "status": result["status"], "expected": expected, "passed": result["status"] == expected, "corrections": result["iteration"], "tool_calls": result["tool_calls"], "elapsed_ms": result["elapsed_ms"], "tokens": result["tokens"]})
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "dataset": "7 fixed synthetic scenarios; one run per mode; no real API or LLM", "limitations": "Not real-world accuracy. Zero tokens reflect rule planner. Timings are local and not statistically significant.", "results": rows}
    Path("docs").mkdir(exist_ok=True)
    Path("docs/evaluation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for mode in (False, True):
        mode_rows = [r for r in rows if r["reflection"] == mode]
        print(f"reflection={mode}: {sum(r['passed'] for r in mode_rows)}/{len(mode_rows)} expected outcomes")


if __name__ == "__main__":
    asyncio.run(main())
