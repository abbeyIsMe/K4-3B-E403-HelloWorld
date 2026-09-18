# CP3 Status

## Checklist against the original hackathon guide

| Requirement | Status | Evidence |
|---|---|---|
| Real AI call in the central decision | Done | `src/grounded_answer.py` calls Gemini; `app.py` uses the result in the answer flow |
| Golden set with at least 20 cases | Done on V2 branch | `eval/golden_set_v2.json` contains 40 cases |
| First measurement table with percentage | Done for retrieval layer | `eval/eval_report_v2.md`: 40/40, 100% |
| Screen recording showing the real AI flow | Done | `demo/Demo_HelloWorld.mp4` is 52.8 seconds and shows the real answer/citation/Inspector flow |
| End-to-end LLM outcome/citation measurement on 20 cases | Done | `eval/eval_report_e2e.md`: 20/20 outcomes and 16/16 ANSWER citation contracts pass |

The original remote `spec.md` was checked before this update. It contains the earlier 12-case CP3 result; the guide's current checkpoint requirement is at least 20 cases. V2 therefore records the stronger 40-case offline retrieval result without rewriting it as an end-to-end LLM score.

## Remaining close-out

1. Submit or link `demo/Demo_HelloWorld.mp4` with the final checkpoint materials.
2. Keep the end-to-end factuality claim qualified as a citation/evidence contract measurement unless the answers receive a separate human claim review.
