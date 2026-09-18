# V2 Offline Evidence Evaluation

## Scope

- Golden set: `eval/golden_set_v2.json`
- Cases: **40** across Day 1–5, source filters, ambiguity, out-of-scope requests, prompt injection, paraphrase and retrieval noise.
- Runner: `scripts/run_eval_v2.py`
- Mode: offline retrieval/evidence evaluation; no LLM call is required.
- Corpus: 672 prepared chunks and existing vector artifacts.

## Result

| Metric | Result |
|---|---:|
| Cases passed | **40 / 40** |
| Evidence/outcome pass rate | **100.0%** |
| Evidence packet support cleanliness | **100.0%** |
| Final LLM factuality | Not measured in this offline run |
| Final LLM citation precision | Not measured in this offline run |

The evaluator treats `FOUND` as `ANSWER` at the retrieval layer. Every returned chunk must be marked `direct` or `contextual`; weak keyword-only candidates are rejected. Contextual support is used only when no direct definition is available and an explanatory relation appears near the queried term. Embedding and PoC Canvas remain explicit definition-gap/not-found cases.

## Reproduce

```bash
.venv/bin/python scripts/run_eval_v2.py
```

This report proves the V2 retrieval/evidence gate. It does not replace the CP3 end-to-end artifact: a real Gemini answer run and a roughly 30-second screen recording are still required by the hackathon guide.
