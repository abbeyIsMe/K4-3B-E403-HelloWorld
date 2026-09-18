# Local Retrieval Regression Report

## Run

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/run_eval_v2.py
.venv/bin/python scripts/run_eval_local_100.py
```

The local suite uses `use_dense=False` and does not call Gemini or any LLM
provider. It is safe to run repeatedly without consuming API quota.

## Result

- Unit tests: **8/8 passed**
- V2 baseline: **40/40 passed**
- Local regression suite: **100/100 passed**
- Compile check: passed

## Coverage

The 100 cases cover the baseline 40 cases plus:

- Accent/no-accent, case, punctuation, and `few-shot` normalization
- Direct definitions and contextual explanations for PII, LLM, RAG, and related terms
- PDF/video source isolation and source leakage checks
- Paraphrases, calculation questions, lookup questions, and schema terms
- Unsupported topics, prompt-injection attempts, and noisy keyword matches
- Ambiguous pronoun/follow-up questions requiring conversation context
- Evidence support values restricted to `direct` or `contextual`

The runner fails on outcome mismatch, disallowed source types, unsupported
evidence labels, or an answer with no retrieved evidence.
