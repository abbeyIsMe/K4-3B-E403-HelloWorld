import os
import sys
import json
import re
import shutil
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
import pypdfium2 as pdfium

# Set page config
st.set_page_config(
    page_title="VLearn NotebookLM — Trợ Lý Bài Giảng",
    page_icon="📓",
    layout="wide",
    initial_sidebar_state="expanded"
)

repo_root = Path(__file__).resolve().parent
sys.path.insert(0, str(repo_root))
load_dotenv(repo_root / ".env")

from src.retrieval import retrieve_evidence
from src.grounded_answer import generate_grounded_answer, get_available_models
from src.query_context import resolve_query


def format_answer_for_display(answer: str, citations: list[dict]) -> str:
    """Replace internal citation IDs with stable, user-facing reference numbers."""
    citation_numbers = {
        citation["chunk_id"]: index
        for index, citation in enumerate(citations, start=1)
    }

    def replace_citation(match):
        number = citation_numbers.get(match.group(1))
        return f"[{number}]" if number else "[nguồn]"

    return re.sub(
        r"\[cite:([^\]]+)\]",
        replace_citation,
        answer,
        flags=re.IGNORECASE,
    )


# Ensure video symlinks directory exists for streaming with clean .mp4 extension
def ensure_video_symlink(video_rel_path: str) -> Path:
    raw_path = repo_root / "materials/raw" / video_rel_path
    if not raw_path.exists():
        return None
    links_dir = repo_root / "materials/derived/video_symlinks"
    links_dir.mkdir(parents=True, exist_ok=True)
    name = raw_path.name
    link_name = name if name.endswith(".mp4") else f"{name}.mp4"
    link_path = links_dir / link_name
    # Keep a real .mp4 file. Serving a symlink to an extensionless source can
    # produce the wrong MIME or Range behavior in Streamlit's media server.
    if (
        link_path.is_symlink()
        or not link_path.is_file()
        or link_path.stat().st_size != raw_path.stat().st_size
    ):
        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()
        temp_path = link_path.with_suffix(".part")
        shutil.copyfile(raw_path, temp_path)
        temp_path.replace(link_path)
    return link_path

# Helper to render PDF page cleanly
@st.cache_data(show_spinner=False)
def render_pdf_page(pdf_relative_path: str, page_num: int):
    try:
        full_path = repo_root / "materials/raw" / pdf_relative_path
        if not full_path.exists():
            return None, f"File không tồn tại: {full_path.name}"
        doc = pdfium.PdfDocument(str(full_path))
        if page_num < 1 or page_num > len(doc):
            return None, f"Trang {page_num} vượt quá số trang ({len(doc)})"
        page = doc[page_num - 1]
        bitmap = page.render(scale=1.8)
        return bitmap.to_pil(), len(doc)
    except Exception as e:
        return None, str(e)

# Initialize session states
if "active_pdf" not in st.session_state:
    st.session_state.active_pdf = None

if "active_video" not in st.session_state:
    st.session_state.active_video = None

if "inspector_mode" not in st.session_state:
    st.session_state.inspector_mode = "📄 Trang Slide PDF"

if "current_query" not in st.session_state:
    st.session_state.current_query = ""

if "query_input" not in st.session_state:
    st.session_state.query_input = ""

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "auto_search" not in st.session_state:
    st.session_state.auto_search = False

if "pending_query" not in st.session_state:
    st.session_state.pending_query = ""

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

LESSON_OPTIONS = {
    "day-01": "Day 01 · AI & LLM Foundation",
    "day-02": "Day 02 · Define Problem For AI",
    "day-03": "Day 03 · Design Pattern ReAct",
    "day-04": "Day 04 · Prompt Engineering & Tool Calling",
    "day-05": "Day 05 · AI Product Thinking & Requirement",
}

# Clean theme-aware CSS
st.markdown("""
<style>
    :root {
        --vlearn-surface: #ffffff;
        --vlearn-ink: #16202a;
        --vlearn-muted: #5f6b76;
        --vlearn-line: #d9e1e8;
        --vlearn-blue: #1976b8;
        --vlearn-red: #c62836;
    }

    .block-container {
        padding-top: 2.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 1500px !important;
    }

    .stApp {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    .vlearn-nav {
        box-sizing: border-box;
        display: flex;
        align-items: center;
        gap: 1.25rem;
        width: calc(100% + 2rem);
        min-height: 4.4rem;
        margin: -1.2rem -1rem 1.8rem;
        padding: 0 1.25rem;
        border-bottom: 1px solid #34373b;
        background: var(--vlearn-surface);
        color: var(--vlearn-ink);
        overflow-x: auto;
        scrollbar-width: none;
    }

    .vlearn-nav::-webkit-scrollbar { display: none; }

    .vlearn-brand {
        display: flex;
        align-items: center;
        flex: 0 0 auto;
        gap: 0.45rem;
        margin-right: clamp(0.2rem, 1.2vw, 1rem);
        font-size: 1.55rem;
        font-weight: 800;
        letter-spacing: 0.01em;
        white-space: nowrap;
    }

    .vlearn-brand-mark {
        display: inline-grid;
        width: 2rem;
        height: 2rem;
        place-items: center;
        color: var(--vlearn-ink);
        font-size: 1.35rem;
        line-height: 1;
    }

    .vlearn-nav-link {
        display: flex;
        align-items: center;
        flex: 0 0 auto;
        gap: 0.4rem;
        height: 4.4rem;
        padding: 0 0.15rem;
        border-bottom: 3px solid transparent;
        color: var(--vlearn-ink);
        font-size: 1rem;
        font-weight: 700;
        white-space: nowrap;
    }

    .vlearn-nav-link.muted { color: var(--vlearn-muted); }
    .vlearn-nav-link.active { border-bottom-color: var(--vlearn-red); color: var(--vlearn-ink); }
    .vlearn-nav-icon { color: var(--vlearn-blue); font-size: 1.05rem; }
    .vlearn-nav-badge {
        padding: 0.15rem 0.45rem;
        border-radius: 999px;
        background: #f2dce0;
        color: #c51f2a;
        font-size: 0.72rem;
        font-weight: 800;
    }

    .vlearn-nav-spacer { flex: 1 1 auto; min-width: 0.5rem; }
    .vlearn-nav-tools {
        display: flex;
        flex: 0 0 auto;
        align-items: center;
        gap: 0.8rem;
        white-space: nowrap;
    }
    .vlearn-locale { color: #ef2732; font-weight: 800; }
    .vlearn-locale.dim { color: #b6b6b6; }
    .vlearn-avatar {
        display: grid;
        width: 2.45rem;
        height: 2.45rem;
        place-items: center;
        border-radius: 50%;
        background: #0ba7e8;
        color: #09202e;
        font-weight: 800;
    }

    .vlearn-nav.dark {
        background: #151515;
        color: #f7f7f7;
    }
    .vlearn-nav.dark .vlearn-nav-link.muted { color: #d7d7d7; }
    .vlearn-nav.dark .vlearn-nav-link.active { color: #ffffff; }
    .vlearn-nav.dark .vlearn-nav-icon { color: #b9dcff; }
    .vlearn-nav.dark .vlearn-locale.dim { color: #b6b6b6; }
    .vlearn-nav.dark .vlearn-brand-mark { color: #ffffff; }

    [data-testid="stChatMessage"] {
        border: 1px solid var(--vlearn-line);
        border-radius: 10px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.7rem;
    }

    [data-testid="stChatMessage"] p { line-height: 1.55; }

    .source-row {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        margin: 0.4rem 0;
        padding: 0.7rem 0.65rem;
        border-radius: 7px;
        font-size: 0.88rem;
    }

    .source-row small {
        display: block;
        margin-top: 0.2rem;
        color: #9aa4ad;
        font-size: 0.75rem;
    }

    .source-active { background: rgba(68, 160, 218, 0.14); border-left: 3px solid #54b8ed; }
    .source-muted { opacity: 0.55; }
    .source-icon { font-size: 1.2rem; }

    div[data-testid="stForm"] {
        border: 1px solid rgba(128, 128, 128, 0.25) !important;
        border-radius: 8px !important;
        padding: 6px 8px !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 8px !important;
        border-color: var(--vlearn-line) !important;
        background: var(--vlearn-surface);
    }

    div[data-testid="stButton"] button {
        min-height: 2.75rem;
        white-space: normal;
        line-height: 1.2;
        overflow-wrap: anywhere;
    }

    div[data-testid="stChatInput"] textarea { min-height: 3rem; }

    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        margin-top: 0.5rem;
    }

    @media (max-width: 900px) {
        .block-container {
            padding: 1.5rem 1rem !important;
        }

        .vlearn-nav {
            margin-left: -1rem;
            margin-right: -1rem;
        }

        .vlearn-nav-link { height: 3.7rem; }
        .vlearn-brand { margin-right: 0; }
        .vlearn-brand-mark { width: 1.6rem; height: 1.6rem; }
        .vlearn-nav-tools { gap: 0.45rem; }
        .vlearn-nav-link { font-size: 0.95rem; }
    }
</style>
""", unsafe_allow_html=True)

if st.session_state.dark_mode:
    st.markdown("""
    <style>
        :root {
            --vlearn-surface: #171b22;
            --vlearn-ink: #f3f4f6;
            --vlearn-muted: #aab4bf;
            --vlearn-line: #303944;
        }
        .stApp { background: #0e1117; color: var(--vlearn-ink); }
    </style>
    """, unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Notebook settings")

    with st.expander("AI provider", expanded=False):
        env_key = os.getenv("GEMINI_API_KEY", "")
        api_key = st.text_input(
            "Google Gemini API Key",
            value=env_key,
            type="password",
            help="Key chỉ dùng trong phiên local này."
        )

        models_list = get_available_models(api_key)
        current_default_model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        default_idx = models_list.index(current_default_model) if current_default_model in models_list else 0
        selected_model = st.selectbox("Mô hình", models_list, index=default_idx)

# Notebook controls
header_title, header_theme, header_clear = st.columns([0.68, 0.20, 0.12], gap="small")
with header_title:
    st.title("Notebook")
    st.caption("Tra cứu bài giảng bằng dẫn chứng trực tiếp từ slide và video")
with header_theme:
    st.markdown("<div style='height: 14px'></div>", unsafe_allow_html=True)
    st.session_state.dark_mode = st.toggle("🌙 Dark", value=st.session_state.dark_mode, key="theme_toggle")
with header_clear:
    st.markdown("<div style='height: 14px'></div>", unsafe_allow_html=True)
    if st.button("🗑 Clear", width="stretch", help="Xoá toàn bộ hội thoại hiện tại"):
        for key, value in {
            "chat_history": [],
            "last_result": None,
            "current_query": "",
            "pending_query": "",
            "active_pdf": None,
            "active_video": None,
            "active_pill": None,
        }.items():
            st.session_state[key] = value
        st.rerun()

# NotebookLM-style workspace: sources, chat, and source inspector.
col_sources, col_studio, col_inspector = st.columns([0.23, 0.49, 0.28], gap="medium")

# --- LEFT COLUMN: SOURCES ---
with col_sources:
    st.markdown("### Sources")
    st.caption("Chọn nguồn được phép dùng làm citation")

    with st.container(border=True):
        st.markdown("**📚 VLearn · kho bài giảng**")
        st.caption("Bật từng ngày để chọn slide/video làm nguồn trả lời")
        st.divider()

        for lesson_id, lesson_name in LESSON_OPTIONS.items():
            with st.expander(lesson_name, expanded=lesson_id == "day-05"):
                st.caption("Chỉ chọn nguồn; artifact không mở hoặc tải từ panel này.")
                st.checkbox(
                    "Slide PDF",
                    value=True,
                    key=f"source_pdf_{lesson_id}",
                )
                st.checkbox(
                    "Video bài giảng",
                    value=True,
                    key=f"source_video_{lesson_id}",
                )

        st.divider()
        st.caption("Citation chỉ lấy từ các Day và loại nguồn đang được tick.")

    allowed_source_map = {
        lesson_id: [
            source_type
            for source_type in ("pdf", "video")
            if st.session_state.get(f"source_{source_type}_{lesson_id}", True)
        ]
        for lesson_id in LESSON_OPTIONS
    }
    selected_lesson_ids = [
        lesson_id for lesson_id, sources in allowed_source_map.items() if sources
    ]
    allowed_sources = [
        source_type
        for source_type in ("pdf", "video")
        if any(source_type in sources for sources in allowed_source_map.values())
    ]
    if selected_lesson_ids:
        last_selected_day = selected_lesson_ids[-1]
        scope_name = f"{LESSON_OPTIONS[selected_lesson_ids[0]]} → {LESSON_OPTIONS[last_selected_day]}"
    else:
        scope_name = "Chưa chọn bài học"
    source_name = " + ".join({"pdf": "slide", "video": "video"}[source] for source in allowed_sources)

    st.metric("Đang chọn", f"{len(selected_lesson_ids)} Day")

# Do not leave an answer from a previous source scope on screen after the
# user changes the lesson or source filters.
scope_signature = (
    tuple(selected_lesson_ids),
    tuple((lesson_id, tuple(sources)) for lesson_id, sources in allowed_source_map.items()),
)
previous_scope = st.session_state.get("scope_signature")
if previous_scope is not None and previous_scope != scope_signature:
    st.session_state.last_result = None
    st.session_state.active_pdf = None
    st.session_state.active_video = None
    st.session_state.chat_history = []
    st.session_state.pending_query = ""
    st.session_state.active_pill = None
st.session_state.scope_signature = scope_signature

# --- CENTER COLUMN: NOTEBOOK CHAT ---
with col_studio:
    # Quick Suggested Questions with native responsive pills
    sample_queries = {
        "💎 Double Diamond": "Quy trình Double Diamond áp dụng cho AI như thế nào?",
        "🔄 ReAct Pattern": "Mô hình ReAct pattern hoạt động ra sao?",
        "🔤 Tokenizer & Token": "Tokenizer là gì và làm nhiệm vụ gì với văn bản?",
        "🧩 JSON Schema Tool": "JSON Schema của Tool là gì?"
    }

    if not st.session_state.chat_history:
        st.caption("💡 Bắt đầu bằng một câu hỏi:")
        selected_pill = st.pills(
            "Gợi ý:",
            options=list(sample_queries.keys()),
            selection_mode="single",
            label_visibility="collapsed",
            key="sample_pill_selector"
        )
        if selected_pill and selected_pill != st.session_state.get("active_pill"):
            st.session_state["active_pill"] = selected_pill
            st.session_state.pending_query = sample_queries[selected_pill]
            st.session_state.auto_search = True
            st.rerun()

    typed_query = st.chat_input(
        "Hỏi về bài giảng đang chọn...",
        key="chat_input",
    )
    form_submitted = typed_query is not None
    auto_search = st.session_state.auto_search
    st.session_state.auto_search = False
    # Only consume a query for the event that created it. A stale pending
    # value must never be treated as a new chat submission on a rerun.
    if form_submitted:
        active_query = typed_query.strip()
        st.session_state.pending_query = ""
    elif auto_search:
        active_query = st.session_state.pending_query.strip()
        st.session_state.pending_query = ""
    else:
        active_query = ""
    should_search = bool(active_query)

    # Execute Search
    if should_search and active_query and active_query.strip():
        st.session_state.current_query = active_query.strip()
        if form_submitted:
            st.session_state.active_pill = None
        if not allowed_sources:
            st.warning("Vui lòng chọn ít nhất một nguồn ở thanh cài đặt bên trái!")
        else:
            with st.spinner(f"Đang tra cứu {scope_name} · nguồn: {source_name}..."):
                query_resolution = resolve_query(
                    active_query,
                    st.session_state.chat_history,
                )
                search_query = query_resolution["query"]
                if query_resolution["status"] == "CLARIFY":
                    ret_res = {
                        "status": "CLARIFY",
                        "reason": query_resolution["reason"],
                        "chunks": [],
                    }
                else:
                    ret_res = retrieve_evidence(
                        query=search_query,
                        lesson_id="all",
                        lesson_ids=selected_lesson_ids,
                        allowed_source_map=allowed_source_map,
                        allowed_sources=allowed_sources
                    )
                grounded_res = generate_grounded_answer(
                    query=search_query,
                    retrieval_result=ret_res,
                    api_key=api_key,
                    model_name=selected_model
                )
                grounded_res["original_query"] = active_query.strip()
                grounded_res["resolved_query"] = search_query
                st.session_state.last_result = grounded_res
                st.session_state.chat_history.append({
                    "query": active_query.strip(),
                    "resolved_query": search_query,
                    "result": grounded_res,
                })
                st.session_state.pending_query = ""
                
                # Auto-populate inspector targets
                cits = grounded_res.get("citations", [])
                echunks = grounded_res.get("evidence_chunks", [])
                
                top_pdf = next((c for c in cits if c["source_type"] == "pdf"), None)
                top_vid = next((c for c in cits if c["source_type"] == "video"), None)
                
                if top_pdf:
                    matched_chk = next((c for c in echunks if c["chunk_id"] == top_pdf["chunk_id"]), None)
                    st.session_state.active_pdf = {
                        "source_name": top_pdf["source_name"],
                        "source_path": top_pdf.get("source_path") or (matched_chk["source_path"] if matched_chk else ""),
                        "page": top_pdf.get("page") or 1,
                        "timestamp_label": top_pdf["timestamp_label"],
                        "lesson_name": matched_chk.get("lesson_name", "") if matched_chk else ""
                    }
                else:
                    st.session_state.active_pdf = None
                    
                if top_vid:
                    matched_chk = next((c for c in echunks if c["chunk_id"] == top_vid["chunk_id"]), None)
                    st.session_state.active_video = {
                        "source_name": top_vid["source_name"],
                        "source_path": top_vid.get("source_path") or (matched_chk["source_path"] if matched_chk else ""),
                        "start_seconds": int(matched_chk.get("start_seconds", 0)) if matched_chk and matched_chk.get("start_seconds") else 0,
                        "timestamp_label": top_vid["timestamp_label"],
                        "lesson_name": matched_chk.get("lesson_name", "") if matched_chk else ""
                    }
                else:
                    st.session_state.active_video = None

                # Auto-switch to video tab if only video cited, otherwise default to PDF
                if top_vid and not top_pdf:
                    st.session_state.inspector_mode = "🎥 Video Bài Giảng"
                elif top_pdf:
                    st.session_state.inspector_mode = "📄 Trang Slide PDF"

    # Display Answer Card
    res = st.session_state.last_result
    for turn in st.session_state.chat_history[:-1]:
        with st.chat_message("user"):
            st.markdown(turn["query"])
        with st.chat_message("assistant"):
            if turn.get("resolved_query") and turn["resolved_query"] != turn["query"]:
                st.caption(f"Ngữ cảnh đã hiểu: {turn['resolved_query']}")
            st.markdown(format_answer_for_display(
                turn["result"]["answer"],
                turn["result"].get("citations", []),
            ))

    if res and st.session_state.chat_history:
        latest_turn = st.session_state.chat_history[-1]
        with st.chat_message("user"):
            st.markdown(latest_turn["query"])
        with st.chat_message("assistant"):
            if latest_turn.get("resolved_query") and latest_turn["resolved_query"] != latest_turn["query"]:
                st.caption(f"Ngữ cảnh đã hiểu: {latest_turn['resolved_query']}")
            outcome = res["outcome"]

            if outcome == "ANSWER":
                st.markdown("✨ **Câu trả lời có kiểm chứng**")
            elif outcome == "CLARIFY":
                st.markdown("⚠️ **Cần làm rõ thêm ngữ cảnh:**")
            else:
                st.markdown("🚫 **Không tìm thấy trong bài giảng:**")

            if res.get("answer_mode") == "GROUNDED_WITH_CONTEXT":
                st.caption("Có phần kiến thức bổ sung được tách riêng, không thuộc slide/video.")

            st.markdown(format_answer_for_display(
                res["answer"],
                res.get("citations", []),
            ))

        citations = res.get("citations", [])
        evidence_chunks = res.get("evidence_chunks", [])

        if evidence_chunks:
            if res["outcome"] == "ANSWER":
                st.caption(f"{len(evidence_chunks)} đoạn evidence được dùng để trả lời")
            else:
                st.caption(f"{len(evidence_chunks)} đoạn evidence liên quan được truy xuất")
        
        if citations:
            st.markdown("##### Nguồn trích dẫn")
            
            pdf_cits = [c for c in citations if c["source_type"] == "pdf"]
            vid_cits = [c for c in citations if c["source_type"] == "video"]
            
            if pdf_cits:
                st.caption("📄 **Slide bài giảng:**")
                p_cols = st.columns(min(2, len(pdf_cits)))
                for i, c in enumerate(pdf_cits):
                    with p_cols[i % len(p_cols)]:
                        matched = next((chk for chk in evidence_chunks if chk["chunk_id"] == c["chunk_id"]), None)
                        location = f"Trang {c.get('page')}" if c.get("page") else c.get("timestamp_label", "Slide")
                        lesson_str = f" · {matched['lesson_name']}" if matched and matched.get("lesson_name") else ""
                        btn_text = f"📄 {location}{lesson_str}"
                        st.caption(c["source_name"])
                        if st.button(btn_text, key=f"btn_p_{i}", width="stretch"):
                            st.session_state.active_pdf = {
                                "source_name": c["source_name"],
                                "source_path": c.get("source_path") or (matched["source_path"] if matched else ""),
                                "page": c.get("page") or 1,
                                "timestamp_label": c["timestamp_label"],
                                "lesson_name": matched.get("lesson_name", "") if matched else ""
                            }
                            st.session_state["inspector_mode"] = "📄 Trang Slide PDF"
                            st.rerun()

            if vid_cits:
                st.caption("🎥 **Video bài giảng:**")
                v_cols = st.columns(min(2, len(vid_cits)))
                for j, v in enumerate(vid_cits):
                    with v_cols[j % len(v_cols)]:
                        matched = next((chk for chk in evidence_chunks if chk["chunk_id"] == v["chunk_id"]), None)
                        lesson_str = f" · {matched['lesson_name']}" if matched and matched.get("lesson_name") else ""
                        btn_text = f"🎥 {v.get('timestamp_label', 'Video')}{lesson_str}"
                        st.caption(v["source_name"])
                        if st.button(btn_text, key=f"btn_v_{j}", width="stretch"):
                            st.session_state.active_video = {
                                "source_name": v["source_name"],
                                "source_path": v.get("source_path") or (matched["source_path"] if matched else ""),
                                "start_seconds": int(matched.get("start_seconds", 0)) if matched and matched.get("start_seconds") else 0,
                                "timestamp_label": v["timestamp_label"],
                                "lesson_name": matched.get("lesson_name", "") if matched else ""
                            }
                            st.session_state["inspector_mode"] = "🎥 Video Bài Giảng"
                            st.rerun()

            with st.expander("📝 Xem các đoạn văn bản gốc (Raw Chunks)"):
                for chk in evidence_chunks:
                    support = chk.get("evidence_support", "direct")
                    st.markdown(f"**{chk.get('lesson_name', '')} · {chk['source_name']} · {chk['timestamp_label']}** · `{support}`")
                    st.text(chk["text"])

# --- RIGHT COLUMN: SOURCE INSPECTOR (PDF & Video Viewer) ---
with col_inspector:
    with st.container(border=True):
        st.markdown("### Source Inspector")
        st.caption("Chọn một citation để mở đúng slide hoặc timestamp video")
        
        col_t1, col_t2 = st.columns(2)
        curr_mode = st.session_state.get("inspector_mode", "📄 Trang Slide PDF")
        
        with col_t1:
            is_pdf = (curr_mode == "📄 Trang Slide PDF")
            if st.button("📄 Trang Slide PDF", type="primary" if is_pdf else "secondary", width="stretch", key="tab_select_pdf"):
                st.session_state["inspector_mode"] = "📄 Trang Slide PDF"
                st.rerun()
                
        with col_t2:
            is_vid = (curr_mode == "🎥 Video Bài Giảng")
            if st.button("🎥 Video Bài Giảng", type="primary" if is_vid else "secondary", width="stretch", key="tab_select_vid"):
                st.session_state["inspector_mode"] = "🎥 Video Bài Giảng"
                st.rerun()
                
        st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
        
        # VIEW 1: PDF Viewer
        if curr_mode == "📄 Trang Slide PDF":
            pdf_data = st.session_state.active_pdf
            if not pdf_data:
                st.info("Chưa có slide được chọn. Bấm một citation ở bên trái để mở nguồn.")
            else:
                st.markdown(f"**Đang xem:** `{pdf_data['source_name']}`")
                if pdf_data.get("lesson_name"):
                    st.caption(f"Bài học: **{pdf_data['lesson_name']}**")
                    
                pdf_path = pdf_data["source_path"]
                curr_p = pdf_data["page"]
                
                img, num_pages = render_pdf_page(pdf_path, curr_p)
                
                # Page Navigator
                p_prev, p_info, p_next = st.columns([1, 2, 1])
                with p_prev:
                    if st.button("◀ Trước", key="p_prev_btn", width="stretch"):
                        if curr_p > 1:
                            pdf_data["page"] -= 1
                            pdf_data["timestamp_label"] = f"Trang {pdf_data['page']}"
                            st.rerun()
                with p_info:
                    pages_str = f"Trang {curr_p} / {num_pages}" if isinstance(num_pages, int) else f"Trang {curr_p}"
                    st.markdown(f"<div style='text-align:center; padding-top:6px; font-weight:600; font-size:0.95rem;'>{pages_str}</div>", unsafe_allow_html=True)
                with p_next:
                    if st.button("Sau ▶", key="p_next_btn", width="stretch"):
                        if isinstance(num_pages, int) and curr_p < num_pages:
                            pdf_data["page"] += 1
                            pdf_data["timestamp_label"] = f"Trang {pdf_data['page']}"
                            st.rerun()
                    
                # Render Image
                if img:
                    st.image(img, width="stretch")
                else:
                    st.error(f"Lỗi đọc PDF: {num_pages}")

        # VIEW 2: Video Player (Seekable & Range-Request Enabled)
        else:
            vid_data = st.session_state.active_video
            if not vid_data:
                st.info("Chưa có video được chọn. Bấm một citation ở bên trái để mở nguồn.")
            else:
                st.markdown(f"**Đang xem:** `{vid_data['source_name']}`")
                if vid_data.get("lesson_name"):
                    st.caption(f"Bài học: **{vid_data['lesson_name']}**")
                    
                vid_path_rel = vid_data["source_path"]
                start_s = vid_data["start_seconds"]
                
                # Resolve clean .mp4 symlink for streaming
                streamable_path = ensure_video_symlink(vid_path_rel)
                
                if streamable_path and streamable_path.exists():
                    st.success(f"⏱️ Mốc trích dẫn: **{vid_data['timestamp_label']}** (tự động nhảy đến giây {start_s})")
                    st.video(str(streamable_path), start_time=int(start_s))
                else:
                    st.error(f"Không thể mở file video: {vid_path_rel}")
