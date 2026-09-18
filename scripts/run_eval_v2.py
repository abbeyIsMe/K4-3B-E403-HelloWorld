"""Offline V2 retrieval/evidence evaluation.

This intentionally does not call an LLM. It measures the evidence packet that
will be sent to the model, so it can run without API quota or credentials.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.retrieval import retrieve_evidence


def run(golden_path: Path) -> int:
    cases = json.loads(golden_path.read_text(encoding="utf-8"))
    passed = 0
    print(f"V2 offline evaluation: {len(cases)} cases")
    for case in cases:
        started = time.perf_counter()
        result = retrieve_evidence(
            case["query"],
            allowed_sources=case.get("allowed_sources", ["pdf", "video"]),
        )
        elapsed = round(time.perf_counter() - started, 3)
        actual = {"FOUND": "ANSWER"}.get(result.get("status"), result.get("status"))
        chunks = result.get("chunks", [])
        actual_types = sorted({chunk.get("source_type") for chunk in chunks})
        expected_types = sorted(case.get("expected_source_types", []))
        outcome_ok = actual == case["expected_outcome"]
        source_ok = actual != "ANSWER" or all(item in expected_types for item in actual_types)
        citation_hint = case.get("expected_citation")
        citation_ok = not citation_hint or any(
            citation_hint in f"{chunk.get('timestamp_label', '')} Trang {chunk.get('page', '')}"
            for chunk in chunks
        )
        clean = all(chunk.get("evidence_support") == "direct" for chunk in chunks)
        ok = outcome_ok and source_ok and citation_ok and clean
        passed += int(ok)
        icon = "PASS" if ok else "FAIL"
        print(f"[{case['id']}] {icon} {actual} {elapsed}s | {case['query']}")
        if not ok:
            print(f"  expected={case['expected_outcome']} sources={expected_types} actual_sources={actual_types}")
    accuracy = round(100 * passed / max(1, len(cases)), 1)
    print(f"Summary: {passed}/{len(cases)} passed ({accuracy}%)")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden", type=Path, default=ROOT / "eval/golden_set_v2.json")
    args = parser.parse_args()
    raise SystemExit(run(args.golden))
