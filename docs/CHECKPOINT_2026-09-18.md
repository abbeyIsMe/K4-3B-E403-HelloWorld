# Checkpoint 2026-09-18

## Repository State

- Branch: `v2-grounded-retrieval`
- Latest commit: `9e68f3a`
- CI: green, including Python tests and Docker build
- Unit tests: `8/8`
- Baseline retrieval evaluation: `40/40`
- Local regression evaluation: `100/100`
- Local-only test command: `python scripts/run_eval_local_100.py`
- `docs/so_tay.md` is intentionally untracked and is not part of the product source.

## What Works

- 375 PDF pages and 16 lecture videos are processed into the local retrieval artifacts.
- The app can retrieve across PDF and video sources and expose source citations.
- PDF citations open the relevant page; video citations seek to the cited timestamp.
- Definition queries are less vulnerable to raw keyword frequency than the original BM25-only flow.
- Contextual explanations are supported when the source mentions a term without a textbook definition.
- Source filters, ambiguous prompts, prompt-injection-style requests, and unsupported topics have regression coverage.
- The test suite runs without Gemini quota. The E2E Gemini suite remains a separate, quota-consuming check.

## Honest Product Assessment

This is a credible grounded lecture-search demo, not yet a full NotebookLM-style assistant.

### Main weaknesses

1. **Conversation memory is shallow.** Chat history is displayed, but follow-up questions are not rewritten against the previous topic. “Còn nhược điểm?” is correctly rejected as ambiguous instead of being resolved from the previous turn.
2. **Retrieval is still partly hand-tuned.** Intent markers, entity aliases, and a few scope guards improve the current corpus but do not generalize to every new lecture or terminology variant.
3. **Citation validation is incomplete.** The system validates that cited IDs exist in the evidence packet, but does not verify that every factual claim is entailed by the cited text.
4. **Clean deployment is incomplete.** `materials/raw` and `materials/derived` are gitignored. A clean Docker checkout has no lecture artifacts unless they are mounted or downloaded during deployment, so the image is buildable but is not self-contained.
5. **Evaluation is retrieval-heavy.** The 100-case suite validates local evidence selection. It does not prove that Gemini produces a correct, concise, Vietnamese answer for every case. The E2E set is much smaller and consumes API quota.
6. **Source quality still has known gaps.** Image-only slide pages need OCR, and ASR/transcript quality can affect video retrieval.
7. **Project documentation is stale in places.** `README.md` and `docs/HANDOFF.md` still describe the earlier 12-case/v1 state and should be synchronized with v2.

## Recommended Next Order

### P0: Make the product deployable

- Package a versioned artifact bundle containing chunks, embeddings, source metadata, and media references.
- Mount or download that bundle in Docker startup and fail with a clear health message when it is missing.
- Add a no-Gemini smoke mode so the deployed UI can be checked without API quota.

### P1: Make the assistant feel intelligent

- Add a query rewrite step for follow-ups using the last grounded subject, with a strict no-guess fallback to `CLARIFY`.
- Add answer-level claim checks or force sentence-level citations in the generation contract.
- Add a compact source preview and “why this evidence” explanation for each citation.

### P2: Improve coverage and polish

- OCR the two image-only slide pages and re-index.
- Re-run a small E2E sample after retrieval changes, using cache and a hard API-call limit.
- Update README, HANDOFF, and changelog to reflect v2 and the 100-case local suite.
