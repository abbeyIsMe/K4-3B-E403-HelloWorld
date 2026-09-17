import os
import sys
import json
import time
from pathlib import Path

# Add project root to sys.path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from src.retrieval import retrieve_evidence
from src.grounded_answer import generate_grounded_answer

def run_evaluation(golden_set_path=None, model_name="gemini-3.1-flash-lite"):
    if golden_set_path is None:
        golden_set_path = repo_root / "eval/golden_set_day01.json"

    with open(golden_set_path, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    print(f"Running evaluation on {len(test_cases)} test cases using model: {model_name}...")
    print("=" * 75)

    results = []
    passed_count = 0

    for tc in test_cases:
        t_start = time.time()
        q = tc["query"]
        sources = tc.get("allowed_sources", ["pdf", "video"])
        
        # 1. Retrieve
        ret = retrieve_evidence(q, allowed_sources=sources)
        
        # 2. Grounded answer
        ans = generate_grounded_answer(q, ret, model_name=model_name)
        elapsed = round(time.time() - t_start, 2)
        
        actual_outcome = ans["outcome"]
        expected_outcome = tc["expected_outcome"]
        
        # Outcome check
        outcome_pass = (actual_outcome == expected_outcome)
        
        # Citation check
        citation_pass = True
        actual_citations = [f"{c['source_name']} ({c['timestamp_label']})" for c in ans.get("citations", [])]
        
        if expected_outcome == "ANSWER":
            expected_cit = tc.get("expected_citation")
            if expected_cit:
                # Check if expected citation matches any actual citation label
                matched = any(expected_cit in c for c in actual_citations)
                citation_pass = matched

        passed = outcome_pass and citation_pass
        if passed:
            passed_count += 1

        res_item = {
            "id": tc["id"],
            "query": q,
            "sources": sources,
            "expected_outcome": expected_outcome,
            "actual_outcome": actual_outcome,
            "expected_citation": tc.get("expected_citation"),
            "actual_citations": actual_citations,
            "outcome_pass": outcome_pass,
            "citation_pass": citation_pass,
            "passed": passed,
            "latency_s": elapsed,
            "answer_preview": ans.get("answer", "")[:120].replace("\n", " ")
        }
        results.append(res_item)
        
        status_icon = "✅ PASS" if passed else "❌ FAIL"
        print(f"[{tc['id']}] {status_icon} | Exp: {expected_outcome:9} | Act: {actual_outcome:9} | Latency: {elapsed}s")
        if not passed:
            print(f"      Q: {q}")
            print(f"      Actual Answer: {res_item['answer_preview']}")
            print(f"      Expected Cit: {tc.get('expected_citation')} | Actual Cits: {actual_citations}")

    accuracy = round((passed_count / len(test_cases)) * 100, 1)
    print("=" * 75)
    print(f"Evaluation Summary: {passed_count}/{len(test_cases)} Passed ({accuracy}%)")
    
    # Save results
    output_json = repo_root / "eval/eval_results_day01.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump({
            "model": model_name,
            "total": len(test_cases),
            "passed": passed_count,
            "accuracy_percent": accuracy,
            "results": results
        }, f, ensure_ascii=False, indent=2)

    # Save markdown report
    output_md = repo_root / "eval/eval_report.md"
    report_lines = [
        "# Báo Cáo Đo Đạc Kiểm Thử (Eval Report) — CP3",
        f"- **Mô hình thử nghiệm:** `{model_name}`",
        f"- **Thời gian chạy:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Tổng số test cases:** {len(test_cases)}",
        f"- **Đạt chuẩn (Passed):** **{passed_count}/{len(test_cases)} ({accuracy}%)**",
        "",
        "## Bảng kết quả chi tiết từng case",
        "",
        "| ID | Câu hỏi | Nguồn chọn | Kỳ vọng | Thực tế | Trích dẫn thực tế | Đánh giá |",
        "|---|---|---|---|---|---|:---:|"
    ]
    for r in results:
        icon = "✅ PASS" if r["passed"] else "❌ FAIL"
        cits = ", ".join(r["actual_citations"][:2]) if r["actual_citations"] else "Không"
        report_lines.append(f"| {r['id']} | {r['query'][:45]}... | {','.join(r['sources'])} | {r['expected_outcome']} | {r['actual_outcome']} | {cits} | {icon} |")
        
    with open(output_md, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")

    print(f"Reports saved to:\n  - {output_json}\n  - {output_md}")
    return accuracy

if __name__ == "__main__":
    run_evaluation()
