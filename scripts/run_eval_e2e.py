"""Quota-safe end-to-end Gemini evaluation.

Retrieval uses BM25 only so each case spends generation quota once (plus one
bounded citation repair if necessary). Results are cached by case ID.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.grounded_answer import generate_grounded_answer
from src.retrieval import retrieve_evidence


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def case_key(case: dict, model: str) -> str:
    raw = json.dumps({"case": case, "model": model}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--model", default="gemini-3.1-flash-lite")
    parser.add_argument("--cache", type=Path, default=ROOT / "eval/e2e_cache.json")
    parser.add_argument("--golden", type=Path, default=ROOT / "eval/golden_set_v2.json")
    args = parser.parse_args()

    if not os.getenv("GEMINI_API_KEY", "").strip():
        print("GEMINI_API_KEY is missing. Load .env before running E2E eval.", file=sys.stderr)
        return 2

    cases = load_json(args.golden, [])[:args.limit]
    cache = load_json(args.cache, {})
    args.cache.parent.mkdir(parents=True, exist_ok=True)
    os.environ["VLEARN_SINGLE_MODEL"] = "1"

    results = []
    calls = 0
    for index, case in enumerate(cases, start=1):
        key = case_key(case, args.model)
        if key in cache:
            result = cache[key]
            # Reconcile expectations when a golden case is corrected without
            # spending another generation call for the cached actual result.
            result["expected_outcome"] = case["expected_outcome"]
            result["passed_outcome"] = result.get("actual_outcome") == case["expected_outcome"]
            print(f"[{index}/{len(cases)}] CACHED {case['id']} -> {result['actual_outcome']}")
            results.append(result)
            continue

        started = time.perf_counter()
        try:
            retrieval = retrieve_evidence(
                case["query"],
                allowed_sources=case.get("allowed_sources", ["pdf", "video"]),
                use_dense=False,
            )
            answer = generate_grounded_answer(
                case["query"],
                retrieval,
                model_name=args.model,
            )
            calls += 1
            item = {
                "id": case["id"],
                "query": case["query"],
                "expected_outcome": case["expected_outcome"],
                "actual_outcome": answer.get("outcome"),
                "expected_citation": case.get("expected_citation"),
                "actual_citations": answer.get("citations", []),
                "answer": answer.get("answer", ""),
                "latency_s": round(time.perf_counter() - started, 2),
                "passed_outcome": answer.get("outcome") == case["expected_outcome"],
            }
            cache[key] = item
            args.cache.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
            results.append(item)
            print(f"[{index}/{len(cases)}] {case['id']} -> {item['actual_outcome']} ({item['latency_s']}s)")
        except Exception as error:
            message = str(error)
            print(f"[{index}/{len(cases)}] STOPPED {case['id']}: {message}", file=sys.stderr)
            if "429" in message or "quota" in message.lower() or "resource_exhausted" in message.lower():
                print("Quota/rate limit detected; cached completed cases were preserved.", file=sys.stderr)
                break
            raise

    passed = sum(item.get("passed_outcome", False) for item in results)
    print(f"Completed: {len(results)}/{len(cases)} cases; API generation calls this run: {calls}")
    print(f"Outcome pass: {passed}/{len(results)}")
    print(f"Cache: {args.cache}")
    return 0 if len(results) == len(cases) and passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
