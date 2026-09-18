# CP3 Status

## Checklist against the original hackathon guide

| Requirement | Status | Evidence |
|---|---|---|
| Real AI call in the central decision | Done | `src/grounded_answer.py` calls Gemini; `app.py` uses the result in the answer flow |
| Golden set with at least 20 cases | Done on V2 branch | `eval/golden_set_v2.json` contains 40 cases |
| First measurement table with percentage | Done for retrieval layer | `eval/eval_report_v2.md`: 40/40, 100% |
| Roughly 30-second screen recording showing the real AI flow | **Missing from this repository** | Add the submitted recording or link before claiming the CP3 artifact complete |
| End-to-end LLM factuality/citation measurement on the 20+ set | **Still required** | The V2 report is intentionally offline and does not measure final Gemini output |

The original remote `spec.md` was checked before this update. It contains the earlier 12-case CP3 result; the guide's current checkpoint requirement is at least 20 cases. V2 therefore records the stronger 30-case offline retrieval result without rewriting it as an end-to-end LLM score.

## Remaining close-out

1. Run the 40-case set through the real Gemini-backed app with credentials available and record outcome, factuality and citation precision.
2. Record a short screen capture: ask a grounded question, show the answer/citation, click the citation, and show the matching PDF page or video timestamp.
3. Update this checklist and the final submission link once those two artifacts exist.
