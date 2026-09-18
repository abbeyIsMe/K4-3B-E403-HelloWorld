# CP3 End-to-End Gemini Evaluation

## Scope

- Golden set: first 20 cases of `eval/golden_set_v2.json`
- Model: `gemini-3.1-flash-lite`
- Retrieval mode: local BM25/evidence gate; no query-embedding call
- Generation: real Gemini API call, cached in the local ignored file `eval/e2e_cache.json`
- Run command:

```bash
.venv/bin/python scripts/run_eval_e2e.py \
  --limit 20 \
  --model gemini-3.1-flash-lite \
  --cache eval/e2e_cache.json
```

## Result

| Metric | Result |
|---|---:|
| Cases completed | **20 / 20** |
| Outcome accuracy | **20 / 20 (100.0%)** |
| ANSWER cases with a valid evidence citation | **15 / 15 (100.0%)** |
| Expected page/timestamp hints matched | **5 / 5 (100.0%)** |
| NOT_FOUND cases without fabricated citations | **5 / 5 (100.0%)** |
| New generation calls in the recorded run | **20** |

The cached result for V2-13 was generated before its expected outcome was corrected from `ANSWER` to `NOT_FOUND`; the actual Gemini outcome was already `NOT_FOUND`, and it is evaluated against the current golden set here.

## Case table

| ID | Expected | Actual | Outcome | Citation contract | Evidence IDs |
|---|---|---|:---:|:---:|---|
| V2-01 | ANSWER | ANSWER | PASS | PASS | `chk_0432` |
| V2-02 | ANSWER | ANSWER | PASS | PASS | `chk_0432` |
| V2-03 | ANSWER | ANSWER | PASS | PASS | `chk_0431` |
| V2-04 | ANSWER | ANSWER | PASS | PASS | `chk_0438`, `chk_0439`, `chk_0442` |
| V2-05 | ANSWER | ANSWER | PASS | PASS | `chk_0438` |
| V2-06 | ANSWER | ANSWER | PASS | PASS | `chk_0197` |
| V2-07 | ANSWER | ANSWER | PASS | PASS | `chk_0102`, `chk_0123` |
| V2-08 | NOT_FOUND | NOT_FOUND | PASS | PASS | - |
| V2-09 | NOT_FOUND | NOT_FOUND | PASS | PASS | - |
| V2-10 | NOT_FOUND | NOT_FOUND | PASS | PASS | - |
| V2-11 | ANSWER | ANSWER | PASS | PASS | `chk_0101` |
| V2-12 | ANSWER | ANSWER | PASS | PASS | `chk_0044` |
| V2-13 | NOT_FOUND | NOT_FOUND | PASS | PASS | - |
| V2-14 | ANSWER | ANSWER | PASS | PASS | `chk_0007` |
| V2-15 | ANSWER | ANSWER | PASS | PASS | `chk_0009` |
| V2-16 | ANSWER | ANSWER | PASS | PASS | `chk_0177`, `chk_0219`, `chk_0231` |
| V2-17 | ANSWER | ANSWER | PASS | PASS | `chk_0100`, `chk_0131`, `chk_0239` |
| V2-18 | ANSWER | ANSWER | PASS | PASS | `chk_0186` |
| V2-19 | NOT_FOUND | NOT_FOUND | PASS | PASS | - |
| V2-20 | NOT_FOUND | NOT_FOUND | PASS | PASS | - |

## Interpretation

This is the CP3 real-AI measurement artifact: Gemini generated the answers, and every answer citation points to an allowed retrieved evidence chunk. The report demonstrates the outcome and citation contract; full claim-by-claim factuality still requires human inspection of each answer against its cited chunk, so the report does not claim that an automated string check proves factuality.

The CP3 screen-recording artifact is `demo/Demo_HelloWorld.mp4` (52.8 seconds), showing a real Gemini answer and the citation/Inspector flow.
