# Changelog

All notable changes to **VLearn NotebookLM** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-09-18 (Release v1.0)

### 🚀 Core Innovations & Features
- **Universal Cross-Day Retrieval:** Enables natural language queries across all 5 lecture days (375 PDF slides + 16 video lectures, ~74 mins total) without students needing to specify the lecture day.
- **Dense Vector Semantic Search (`gemini-embedding-001`):**
  - All 672 chunks indexed into a 3072-dimensional vector space stored in `materials/derived/embeddings/embeddings.npy` (7.9 MB) with $L_2$ normalization for instantaneous cosine similarity.
  - Implemented batch indexer with automatic rate limit backoff and checkpoint resumption (`scripts/build_vector_index.py`).
- **Intent-Aware Contextual Reranking Engine:**
  - Classifies query intent: Definition (`là gì`, `khái niệm`, `định nghĩa`), Workflow/Procedure (`quy trình`, `bước`, `flow`), Calculation/Budget (`tính toán`, `ngân sách`, `bao nhiêu`).
  - Definitional queries apply a +15.0 boost to predicate definition contexts (`được gọi là [X]`, `[X] là công cụ để...`, `[X] chính là...`) and penalize numerical/parameter mentions without semantic definition.
  - Fixes the false-positive keyword problem (e.g. asking *"Token là gì?"* prioritizes the actual definition in `Day1-Token-Context.mp4` 00:43-00:56 over arithmetic budget chunks).
- **Reciprocal Rank Fusion (RRF):**
  - Combines Dense Vector rank and Intent-Boosted BM25 rank with balanced dual-source allocation ($k$ PDF + $k$ Video).
- **Synchronized Dual-Source Inspector:**
  - **PDF Viewer:** Automatically renders the exact physical page using `pypdfium2` with compact, responsive page navigation.
  - **Video Player:** Automatically seeks to the exact `start_time` timestamp. Clean symlinks at `materials/derived/video_symlinks/*.mp4` resolve extensionless Google Drive videos and enable native HTTP 206 Partial Content Range Requests.
  - **Dynamic Two-Way Tab Syncing:** Clicking a PDF citation button lights up the PDF tab; clicking a Video citation button lights up the Video tab and seeks immediately.
- **Strict Grounding & Citation Filtering:**
  - Instructions enforce that the LLM only cites evidence that directly answers the question.
  - Only chunks actually cited in the LLM's answer text are displayed as interactive citation chips in the UI.

### 🐛 Bug Fixes & Stability
- **Fixed Streamlit Tab Switching:** Replaced static `st.tabs` with state-synchronized dynamic buttons (`col_t1, col_t2`) bound to `st.session_state.inspector_mode`.
- **Fixed Video Seeking:** Removed unsupported `key` parameter from `st.video()` to prevent `TypeError: MediaMixin.video() got an unexpected keyword argument 'key'`.
- **Fixed Responsive Header Clipping:** Removed aggressive `padding-top: 1.2rem` and global column overrides that caused header text to hide under Streamlit's navbar. Restored safe top padding (`4.5rem`) with native Streamlit `st.title` and `st.caption`.
- **Fixed Button Squashing:** Replaced `st.columns(4)` query suggestions with auto-wrapping `st.pills`.

### 🧪 Evaluation & Quality
- Golden evaluation test suite (`scripts/run_eval.py`) running on 12 ground-truth test cases across Day 1 to Day 5:
  - **Score:** 12 / 12 Passed (**100.0% accuracy**).
  - Outcome precision: 100% on `ANSWER`, `CLARIFY`, and `NOT_FOUND`.

---

## [0.2.0] - 2026-09-17 (Checkpoints CP1 - CP3)

### Added
- Complete raw data audit for 21 files (5 PDFs + 16 MP4s).
- Whisper ASR transcription for all 16 videos via `faster-whisper` (`int8` on CPU).
- PDF text extraction for 373 text pages via `pypdfium2`.
- Initial BM25 sparse retriever and ambiguity detection logic.
- Grounded prompt engineering with fallback to deterministic citation extraction.
