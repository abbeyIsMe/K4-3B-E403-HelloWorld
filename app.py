import os
import sys
import json
import re
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
import pypdfium2 as pdfium

# Set page config
st.set_page_config(
    page_title="VLearn NotebookLM — Trợ Lý Bài Giảng",
    page_icon="📓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

repo_root = Path(__file__).resolve().parent
sys.path.insert(0, str(repo_root))
load_dotenv(repo_root / ".env")

from src.retrieval import retrieve_evidence
from src.grounded_answer import generate_grounded_answer, get_available_models


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
    if not link_path.exists():
        link_path.symlink_to(raw_path)
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

# Clean theme-aware CSS
st.markdown("""
<style>
    .block-container {
        padding-top: 2.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 1500px !important;
    }

    .stApp {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    div[data-testid="stForm"] {
        border: 1px solid rgba(128, 128, 128, 0.25) !important;
        border-radius: 8px !important;
        padding: 6px 8px !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 8px !important;
    }

    div[data-testid="stButton"] button {
        min-height: 2.35rem;
        white-space: normal;
        line-height: 1.2;
    }

    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        margin-top: 0.5rem;
    }

    @media (max-width: 900px) {
        .block-container {
            padding: 1.5rem 1rem !important;
        }
    }
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

    st.subheader("Phạm vi nguồn")
    
    lesson_options = {
        "all": "🔍 Toàn Bộ Khóa Học (Day 1 → Day 5)",
        "day-01": "Day 01: AI & LLM Foundation",
        "day-02": "Day 02: Define Problem For AI",
        "day-03": "Day 03: Design Pattern ReAct",
        "day-04": "Day 04: Prompt Engineering & Tool Calling",
        "day-05": "Day 05: AI Product Thinking & Requirement"
    }
    
    selected_lesson_key = st.selectbox(
        "Lọc bài học:",
        options=list(lesson_options.keys()),
        format_func=lambda k: lesson_options[k],
        index=0
    )
    
    use_pdf = st.checkbox("📄 Slide bài giảng (5 PDFs)", value=True)
    use_video = st.checkbox("🎥 Video bài giảng (16 Videos)", value=True)
    
    allowed_sources = []
    if use_pdf:
        allowed_sources.append("pdf")
    if use_video:
        allowed_sources.append("video")
        
    st.caption("375 trang slide · 16 video · 672 evidence chunks")

# Do not leave an answer from a previous source scope on screen after the
# user changes the lesson or source filters.
scope_signature = (selected_lesson_key, tuple(allowed_sources))
previous_scope = st.session_state.get("scope_signature")
if previous_scope is not None and previous_scope != scope_signature:
    st.session_state.last_result = None
    st.session_state.active_pdf = None
    st.session_state.active_video = None
    st.session_state.chat_history = []
    st.session_state.pending_query = ""
    st.session_state.active_pill = None
st.session_state.scope_signature = scope_signature

scope_name = lesson_options[selected_lesson_key]
source_name = " + ".join(
    {"pdf": "slide", "video": "video"}[source] for source in allowed_sources
)

# Top Header
st.title("📓 VLearn NotebookLM")
st.caption("Tra cứu bài giảng bằng dẫn chứng trực tiếp từ slide và video")

# Main layout gives the answer more room than the inspector.
col_studio, col_inspector = st.columns([1.2, 0.8], gap="large")

# --- LEFT COLUMN: NOTEBOOK STUDIO (Chat & Citations) ---
with col_studio:
    # Quick Suggested Questions with native responsive pills
    sample_queries = {
        "💎 Double Diamond": "Quy trình Double Diamond áp dụng cho AI như thế nào?",
        "🔄 ReAct Pattern": "Mô hình ReAct pattern hoạt động ra sao?",
        "🔤 Tokenizer & Token": "Tokenizer là gì và làm nhiệm vụ gì với văn bản?",
        "🧩 JSON Schema Tool": "JSON Schema của Tool là gì?"
    }

    st.caption("💡 Gợi ý câu hỏi nghiên cứu:")
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
                ret_res = retrieve_evidence(
                    query=active_query.strip(),
                    lesson_id=selected_lesson_key,
                    allowed_sources=allowed_sources
                )
                grounded_res = generate_grounded_answer(
                    query=active_query.strip(),
                    retrieval_result=ret_res,
                    api_key=api_key,
                    model_name=selected_model
                )
                st.session_state.last_result = grounded_res
                st.session_state.chat_history.append({
                    "query": active_query.strip(),
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
            st.markdown(format_answer_for_display(
                turn["result"]["answer"],
                turn["result"].get("citations", []),
            ))

    if res and st.session_state.chat_history:
        latest_turn = st.session_state.chat_history[-1]
        with st.chat_message("user"):
            st.markdown(latest_turn["query"])
        outcome = res["outcome"]
        
        if outcome == "ANSWER":
            st.markdown("✨ **Câu trả lời có kiểm chứng**")
        elif outcome == "CLARIFY":
            st.markdown("⚠️ **Cần làm rõ thêm ngữ cảnh:**")
        else:
            st.markdown("🚫 **Không tìm thấy trong bài giảng:**")
            
        with st.container(border=True):
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
