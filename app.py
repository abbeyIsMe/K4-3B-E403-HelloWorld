import os
import sys
import json
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

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "auto_search" not in st.session_state:
    st.session_state.auto_search = False

# Clean theme-aware CSS
st.markdown("""
<style>
    /* Ensure top content is never cut off by Streamlit header */
    .block-container {
        padding-top: 4.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 1380px !important;
    }
    
    /* Clean modern typography */
    .stApp {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Form container styling */
    div[data-testid="stForm"] {
        border: 1px solid rgba(128, 128, 128, 0.25) !important;
        border-radius: 12px !important;
        padding: 8px 12px !important;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Cấu Hình Notebook")
    
    env_key = os.getenv("GEMINI_API_KEY", "")
    api_key = st.text_input(
        "Google Gemini API Key",
        value=env_key,
        type="password",
        help="Lấy miễn phí tại https://aistudio.google.com"
    )
    
    models_list = get_available_models(api_key)
    current_default_model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    default_idx = models_list.index(current_default_model) if current_default_model in models_list else 0
    
    selected_model = st.selectbox(
        "Mô hình AI",
        models_list,
        index=default_idx
    )
    
    st.divider()
    st.subheader("📁 Nguồn Tài Liệu (375 Slides & 16 Videos)")
    
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
        
    st.divider()
    st.caption("NotebookLM for VLearn — Batch 04 Hackathon Project")

# Top Header
st.title("📓 VLearn NotebookLM")
st.caption("Trợ lý tra cứu bài giảng thông minh — Dẫn chứng trực tiếp từ 5 Slide PDF & 16 Video bài giảng")
st.divider()

# Main Two-Column Studio Layout (NotebookLM Style)
col_studio, col_inspector = st.columns([1, 1], gap="medium")

# --- LEFT COLUMN: NOTEBOOK STUDIO (Chat & Citations) ---
with col_studio:
    # Quick Suggested Questions with native responsive pills
    sample_queries = {
        "💎 Double Diamond": "Quy trình Double Diamond áp dụng cho AI như thế nào?",
        "🔄 ReAct Pattern": "Mô hình ReAct pattern hoạt động ra sao?",
        "🔤 Tokenizer & Token": "Tokenizer là gì và làm nhiệm vụ gì với văn bản?",
        "📋 PoC Canvas": "PoC Canvas dùng để làm gì trong AI Product?"
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
        st.session_state.current_query = sample_queries[selected_pill]
        st.session_state.auto_search = True
        st.rerun()

    # Search Bar with Enter key support
    with st.form("query_form", clear_on_submit=False):
        c_in, c_btn = st.columns([5, 1])
        with c_in:
            typed_query = st.text_input(
                "Nhập câu hỏi nghiên cứu:",
                value=st.session_state.current_query,
                placeholder="Đặt câu hỏi về bất kỳ bài học nào rồi nhấn Enter...",
                label_visibility="collapsed"
            )
        with c_btn:
            form_submitted = st.form_submit_button("Hỏi AI", type="primary", use_container_width=True)

    should_search = form_submitted or st.session_state.auto_search
    st.session_state.auto_search = False
    active_query = typed_query if form_submitted else st.session_state.current_query

    # Execute Search
    if should_search and active_query and active_query.strip():
        st.session_state.current_query = active_query.strip()
        if not allowed_sources:
            st.warning("Vui lòng chọn ít nhất một nguồn ở thanh cài đặt bên trái!")
        else:
            with st.spinner("Đang tra cứu xuyên suốt 5 bài học và trích xuất dẫn chứng..."):
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
    if res:
        outcome = res["outcome"]
        
        if outcome == "ANSWER":
            st.markdown("✨ **Câu trả lời có kiểm chứng (Grounded Answer):**")
        elif outcome == "CLARIFY":
            st.markdown("⚠️ **Cần làm rõ thêm ngữ cảnh:**")
        else:
            st.markdown("🚫 **Không tìm thấy trong bài giảng:**")
            
        with st.container(border=True):
            st.markdown(res["answer"])

        citations = res.get("citations", [])
        evidence_chunks = res.get("evidence_chunks", [])
        
        if citations:
            st.markdown("##### 🔗 Nguồn trích dẫn (Bấm để nhảy nguồn bên phải):")
            
            pdf_cits = [c for c in citations if c["source_type"] == "pdf"]
            vid_cits = [c for c in citations if c["source_type"] == "video"]
            
            if pdf_cits:
                st.caption("📄 **Slide bài giảng:**")
                p_cols = st.columns(min(2, len(pdf_cits)))
                for i, c in enumerate(pdf_cits):
                    with p_cols[i % len(p_cols)]:
                        matched = next((chk for chk in evidence_chunks if chk["chunk_id"] == c["chunk_id"]), None)
                        lesson_str = f" · {matched['lesson_name']}" if matched and matched.get("lesson_name") else ""
                        btn_text = f"📄 [{c['timestamp_label']}] {c['source_name']}{lesson_str}"
                        if st.button(btn_text, key=f"btn_p_{i}", use_container_width=True):
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
                        btn_text = f"🎥 [{v['timestamp_label']}] {v['source_name']}{lesson_str}"
                        if st.button(btn_text, key=f"btn_v_{j}", use_container_width=True):
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
                    st.markdown(f"**[{chk.get('lesson_name', '')} | {chk['source_name']} | {chk['timestamp_label']}]**")
                    st.text(chk["text"])

# --- RIGHT COLUMN: SOURCE INSPECTOR (PDF & Video Viewer) ---
with col_inspector:
    with st.container(border=True):
        st.markdown("### 🔍 Source Inspector")
        st.caption("Trực quan hóa tài liệu và vị trí đoạn video đang được trích dẫn")
        
        col_t1, col_t2 = st.columns(2)
        curr_mode = st.session_state.get("inspector_mode", "📄 Trang Slide PDF")
        
        with col_t1:
            is_pdf = (curr_mode == "📄 Trang Slide PDF")
            if st.button("📄 Trang Slide PDF", type="primary" if is_pdf else "secondary", use_container_width=True, key="tab_select_pdf"):
                st.session_state["inspector_mode"] = "📄 Trang Slide PDF"
                st.rerun()
                
        with col_t2:
            is_vid = (curr_mode == "🎥 Video Bài Giảng")
            if st.button("🎥 Video Bài Giảng", type="primary" if is_vid else "secondary", use_container_width=True, key="tab_select_vid"):
                st.session_state["inspector_mode"] = "🎥 Video Bài Giảng"
                st.rerun()
                
        st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
        
        # VIEW 1: PDF Viewer
        if curr_mode == "📄 Trang Slide PDF":
            pdf_data = st.session_state.active_pdf
            if not pdf_data:
                st.info("Chưa có trích dẫn Slide PDF nào được chọn.")
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
                    if st.button("◀ Trước", key="p_prev_btn", use_container_width=True):
                        if curr_p > 1:
                            pdf_data["page"] -= 1
                            pdf_data["timestamp_label"] = f"Trang {pdf_data['page']}"
                            st.rerun()
                with p_info:
                    pages_str = f"Trang {curr_p} / {num_pages}" if isinstance(num_pages, int) else f"Trang {curr_p}"
                    st.markdown(f"<div style='text-align:center; padding-top:6px; font-weight:600; font-size:0.95rem;'>{pages_str}</div>", unsafe_allow_html=True)
                with p_next:
                    if st.button("Sau ▶", key="p_next_btn", use_container_width=True):
                        if isinstance(num_pages, int) and curr_p < num_pages:
                            pdf_data["page"] += 1
                            pdf_data["timestamp_label"] = f"Trang {pdf_data['page']}"
                            st.rerun()
                    
                # Render Image
                if img:
                    st.image(img, use_container_width=True)
                else:
                    st.error(f"Lỗi đọc PDF: {num_pages}")

        # VIEW 2: Video Player (Seekable & Range-Request Enabled)
        else:
            vid_data = st.session_state.active_video
            if not vid_data:
                st.info("Chưa có trích dẫn Video nào được chọn.")
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
