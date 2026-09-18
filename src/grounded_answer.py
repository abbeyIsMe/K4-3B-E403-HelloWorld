import os
import re
import json
import warnings
from pathlib import Path
from dotenv import load_dotenv

# Suppress AFC deprecation warning from Google GenAI SDK
warnings.filterwarnings("ignore", message=".*Direct use of automatic function calling.*")

repo_root = Path(__file__).resolve().parent.parent
load_dotenv(repo_root / ".env")

# Verified active models for current API keys
WORKING_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite-preview"
]

def get_available_models(api_key: str = None):
    """Return verified available flash models."""
    return WORKING_MODELS


def _citation_from_chunk(chunk: dict) -> dict:
    return {
        "chunk_id": chunk["chunk_id"],
        "source_type": chunk["source_type"],
        "source_name": chunk["source_name"],
        "page": chunk.get("page"),
        "timestamp_label": chunk.get("timestamp_label"),
        "source_path": chunk["source_path"]
    }


def generate_grounded_answer(query: str, retrieval_result: dict, api_key: str = None, model_name: str = None):
    """
    Generate grounded answer from retrieved chunks.
    Ensures citations match real retrieved chunk metadata and cites BOTH PDF and Video when available.
    """
    status = retrieval_result.get("status")
    
    if status == "CLARIFY":
        return {
            "outcome": "CLARIFY",
            "answer": retrieval_result.get("reason", "Câu hỏi còn mơ hồ, vui lòng cung cấp thêm ngữ cảnh cụ thể."),
            "citations": [],
            "evidence_chunks": []
        }
        
    if status != "FOUND" or not retrieval_result.get("chunks"):
        return {
            "outcome": "NOT_FOUND",
            "answer": "Không tìm thấy nội dung liên quan trong các nguồn bài giảng đã chọn. Trợ lý VLearn tuân thủ nguyên tắc không suy đoán hoặc bù kiến thức ngoài bài học.",
            "citations": [],
            "evidence_chunks": []
        }

    chunks = retrieval_result["chunks"]
    citations = [_citation_from_chunk(chk) for chk in chunks]

    # Prepare context for LLM
    context_blocks = []
    for i, chk in enumerate(chunks, 1):
        lbl = chk["timestamp_label"]
        src_type_label = "SLIDE PDF" if chk["source_type"] == "pdf" else "VIDEO BÀI GIẢNG"
        context_blocks.append(f"--- DẪN CHỨNG {i} [{src_type_label}: {chk['source_name']} | {lbl} | id:{chk['chunk_id']}] ---\n{chk['text']}")
    context_text = "\n\n".join(context_blocks)

    key = api_key or os.getenv("GEMINI_API_KEY")
    selected_model = model_name or os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    
    if "2.5" in selected_model or "2.0" in selected_model:
        selected_model = "gemini-3.1-flash-lite"

    # If API Key is available, call Gemini
    if key and key.strip():
        if os.getenv("VLEARN_SINGLE_MODEL", "").lower() in {"1", "true", "yes"}:
            models_to_try = [selected_model]
        else:
            models_to_try = [selected_model] + [m for m in WORKING_MODELS if m != selected_model]
        
        from google import genai
        client = genai.Client(api_key=key.strip())
        
        citation_instruction = "Ở cuối mỗi ý chính, BẮT BUỘC trích dẫn đúng chunk ID theo định dạng `[cite:CHUNK_ID]`. Chỉ dùng ID có trong evidence và không tự bịa ID."

        prompt = f"""Bạn là trợ lý học tập VLearn trung thực và chính xác. 
Nhiệm vụ của bạn là trả lời câu hỏi của học viên CHỈ DỰA TRÊN các đoạn dẫn chứng (Evidence) dưới đây.

QUY TẮC BẮT BUỘC:
1. {citation_instruction}
2. Chỉ sử dụng thông tin có trong các đoạn dẫn chứng. Tuyệt đối KHÔNG sử dụng kiến thức bên ngoài và KHÔNG được suy diễn/bịa đặt.
3. Chỉ trích dẫn các đoạn dẫn chứng THỰC SỰ trả lời cho câu hỏi. KHÔNG trích dẫn các đoạn chỉ vô tình xuất hiện từ khóa nhưng nói về vấn đề khác. Không cần cố dùng cả slide và video.
4. Nếu các đoạn dẫn chứng KHÔNG chứa câu trả lời trực tiếp hoặc thông tin không đủ, hãy trả lời chính xác: "Chưa tìm thấy thông tin này trong các nguồn bài giảng đã chọn."
5. Trình bày rõ ràng, súc tích bằng tiếng Việt.

CÁC ĐOẠN DẪN CHỨNG:
{context_text}

CÂU HỎI CỦA HỌC VIÊN:
{query}
"""
        for m in models_to_try:
            try:
                chat = client.chats.create(model=m)
                response = chat.send_message(prompt)
                raw_answer = response.text.strip()
                
                if "chưa tìm thấy thông tin" in raw_answer.lower() or "không tìm thấy thông tin" in raw_answer.lower():
                    return {
                        "outcome": "NOT_FOUND",
                        "answer": raw_answer,
                        "citations": [],
                        "evidence_chunks": chunks
                    }

                valid_ids = {chk["chunk_id"]: chk for chk in chunks}
                cited_ids = []
                for cid in re.findall(r"\[cite:([^\]]+)\]", raw_answer, flags=re.IGNORECASE):
                    cid = cid.strip()
                    if cid in valid_ids and cid not in cited_ids:
                        cited_ids.append(cid)
                used_citations = [_citation_from_chunk(valid_ids[cid]) for cid in cited_ids]

                # Never silently attach top chunks to an uncited answer. A
                # bounded retry below gives the model one chance to repair it.
                if not used_citations:
                    retry_prompt = prompt + "\n\nVALIDATION ERROR: Câu trả lời trước thiếu [cite:CHUNK_ID]. Hãy viết lại ngắn gọn và thêm ít nhất một citation ID hợp lệ."
                    try:
                        retry_chat = client.chats.create(model=m)
                        retry_response = retry_chat.send_message(retry_prompt)
                        raw_answer = (retry_response.text or "").strip()
                        cited_ids = [
                            cid.strip() for cid in re.findall(r"\[cite:([^\]]+)\]", raw_answer, flags=re.IGNORECASE)
                            if cid.strip() in valid_ids
                        ]
                        used_citations = [_citation_from_chunk(valid_ids[cid]) for cid in dict.fromkeys(cited_ids)]
                    except Exception as retry_error:
                        print(f"Citation repair failed ({retry_error})")
                if not used_citations:
                    continue

                return {
                    "outcome": "ANSWER",
                    "answer": raw_answer,
                    "citations": used_citations,
                    "evidence_chunks": chunks
                }
            except Exception as e:
                print(f"Model {m} failed ({e}), trying next model...")

    # Offline fallback is allowed only after the evidence gate has produced
    # direct evidence. It never uses arbitrary retrieval candidates.
    top_chunks = chunks[:2]
    summaries = []
    for tc in top_chunks:
        lead_text = tc["text"].replace("\n", " ").strip()
        if len(lead_text) > 200:
            lead_text = lead_text[:200] + "..."
        summaries.append(f"- Theo {tc['source_name']} ({tc['timestamp_label']}): {lead_text}")
        
    answer = "\n".join(summaries)
    
    return {
        "outcome": "ANSWER",
        "answer": answer,
        "citations": citations,
        "evidence_chunks": chunks
    }
