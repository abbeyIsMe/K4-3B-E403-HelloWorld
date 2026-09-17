import re
import math
import json
from pathlib import Path
from collections import Counter

VIETNAMESE_STOPWORDS = {
    "là", "gì", "thế", "nào", "như", "sao", "làm", "cách", "ở", "đâu", "khi",
    "và", "với", "cho", "của", "được", "có", "không", "những", "các", "một",
    "thì", "mà", "đến", "từ", "vào", "ra", "đã", "đang", "sẽ", "phải", "bị",
    "bạn", "mình", "em", "anh", "chị", "tôi", "này", "đó", "kia", "ạ", "nhé",
    "nhỉ", "hả", "nữa", "rồi", "lại", "thôi"
}

class BM25Retriever:
    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.chunks = []
        self.doc_len = []
        self.avgdl = 0
        self.doc_freqs = Counter()
        self.term_freqs = []

    @staticmethod
    def tokenize(text, remove_stopwords=False):
        if not text:
            return []
        clean_text = re.sub(r"[^\w\s\d]", " ", text.lower())
        tokens = [t for t in clean_text.split() if len(t) > 1]
        if remove_stopwords:
            tokens = [t for t in tokens if t not in VIETNAMESE_STOPWORDS]
        return tokens

    def index(self, chunks):
        self.chunks = chunks
        self.doc_len = []
        self.term_freqs = []
        self.doc_freqs = Counter()
        
        for chk in chunks:
            tokens = self.tokenize(chk["text"], remove_stopwords=False)
            self.doc_len.append(len(tokens))
            t_counter = Counter(tokens)
            self.term_freqs.append(t_counter)
            for token in t_counter:
                self.doc_freqs[token] += 1
                
        self.avgdl = (sum(self.doc_len) / len(self.doc_len)) if self.doc_len else 0

    def search(self, query, top_k=3):
        q_all_tokens = self.tokenize(query, remove_stopwords=False)
        q_content_tokens = self.tokenize(query, remove_stopwords=True)
        
        if not q_all_tokens:
            return []

        scores = []
        n_docs = len(self.chunks)

        for i, chk in enumerate(self.chunks):
            doc_freq = self.term_freqs[i]
            dl = self.doc_len[i]

            # Require at least 1 content word to match if content words exist
            if q_content_tokens:
                content_matches = [t for t in q_content_tokens if t in doc_freq]
                if not content_matches:
                    continue

            score = 0.0
            for t in q_all_tokens:
                if t in doc_freq:
                    tf = doc_freq[t]
                    df = self.doc_freqs[t]
                    weight = 2.0 if t in q_content_tokens else 0.2
                    idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * (dl / (self.avgdl + 1e-9)))
                    score += weight * idf * (numerator / denominator)

            # Intent & Context Reranking Boost
            context_boost = score_context_intent(query, chk)
            final_score = max(0.0, score + context_boost)

            if final_score > 0.0:
                scores.append((final_score, chk))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [(chk, s) for s, chk in scores[:top_k]]


def score_context_intent(query: str, chk: dict) -> float:
    """
    Evaluate contextual relevance beyond raw keyword counts.
    Detects if the user query is asking for:
    1. Definition/Concept ('là gì', 'khái niệm', 'định nghĩa', 'ý nghĩa')
    2. Workflow/Procedure ('quy trình', 'các bước', 'cách thức', 'hoạt động ra sao')
    3. Calculation/Budget ('tính toán', 'ngân sách', 'bao nhiêu token', 'giới hạn')
    """
    q = query.lower().strip()
    text = chk.get("text", "").lower()
    boost = 0.0
    
    is_def = any(p in q for p in ["là gì", "khái niệm", "định nghĩa", "thế nào là", "ý nghĩa của", "bản chất"])
    is_proc = any(p in q for p in ["quy trình", "các bước", "làm sao", "cách", "hoạt động ra sao", "pattern"])
    is_calc = any(p in q for p in ["tính", "ngân sách", "bao nhiêu", "giới hạn", "context window", "chi phí"])
    
    # Common core AI terms across the 5 course days
    core_terms = [
        "token", "tokenizer", "react", "double diamond", "poc canvas",
        "system prompt", "context window", "fine-tuning", "hallucination",
        "rag", "tool calling", "function calling", "embedding", "temperature",
        "top_p", "few-shot", "zero-shot", "agent"
    ]
    
    for term in core_terms:
        if term in q:
            if is_def:
                # Strong definition indicators
                def_patterns = [
                    rf"được gọi là\s+{re.escape(term)}",
                    rf"{re.escape(term)}\s+là\s+",
                    rf"{re.escape(term)}\s+chính là",
                    rf"khái niệm\s+(?:về\s+)?{re.escape(term)}",
                    rf"định nghĩa\s+(?:về\s+)?{re.escape(term)}",
                    rf"{re.escape(term)}\s+đóng vai trò",
                    rf"công cụ.*{re.escape(term)}",
                    rf"bộ tách token,\s*{re.escape(term)}"
                ]
                for pat in def_patterns:
                    if re.search(pat, text):
                        boost += 15.0
                        break
                
                # Demote purely numerical / parameter occurrences when asking for definition
                param_patterns = [
                    rf"\d+\s*{re.escape(term)}",
                    rf"max_{re.escape(term)}s?",
                    rf"chi phí\s+{re.escape(term)}",
                    rf"ngân sách\s+{re.escape(term)}"
                ]
                if any(re.search(p, text) for p in param_patterns) and boost == 0.0:
                    boost -= 6.0
                    
            elif is_proc:
                proc_patterns = [
                    rf"quy trình\s+(?:của\s+)?{re.escape(term)}",
                    rf"giai đoạn\s+(?:của\s+)?{re.escape(term)}",
                    rf"bước\s+\d+",
                    rf"vòng lặp|chu trình|flow"
                ]
                if any(re.search(pat, text) for pat in proc_patterns):
                    boost += 10.0
                    
            elif is_calc:
                calc_patterns = [
                    rf"\d+\s*{re.escape(term)}",
                    rf"ngân sách|giới hạn|tính toán|cộng|trừ"
                ]
                if any(re.search(pat, text) for pat in calc_patterns):
                    boost += 8.0
                    
    return boost


def is_query_ambiguous(query: str) -> bool:
    """Detect if question is too vague, generic, or lacks substantive context."""
    q = query.strip().lower()
    clean = re.sub(r"[^\w\s]", "", q)
    words = clean.split()
    
    if len(words) <= 2:
        return True
        
    ambiguous_patterns = [
        r"^(cái này|chỗ này|đoạn này|nó) (dùng|là|làm|như thế nào|thế nào|sao)",
        r"^(giải thích|làm rõ|hướng dẫn|chỉ em) (đi|với|giúp|nhé|ạ)?$",
        r"^(cái này|chỗ này|phần này) nghĩa là gì",
        r"^làm sao để làm (được|ạ)?$",
        r"^(em|mình) không hiểu (gì cả|ạ)?$",
        r"^cho em hỏi (chút|với|này|ạ)?$"
    ]
    for p in ambiguous_patterns:
        if re.search(p, q):
            return True
            
    return False


def retrieve_evidence(query: str, lesson_id="all", allowed_sources=None, top_k=3, min_score=2.0):
    """
    Retrieve candidate chunks with dual-source balancing (PDF and Video).
    top_k: Number of top chunks per source type (e.g. 3 PDF + 3 Video).
    """
    if allowed_sources is None:
        allowed_sources = ["pdf", "video"]
        
    repo_root = Path(__file__).resolve().parent.parent
    chunks_file = repo_root / "materials/derived/chunks/all_chunks.jsonl"
    
    if not chunks_file.exists():
        chunks_file = repo_root / f"materials/derived/chunks/{lesson_id}_chunks.jsonl"
        
    if not chunks_file.exists():
        return {
            "status": "ERROR",
            "message": "Không tìm thấy dữ liệu index bài học.",
            "chunks": []
        }

    pdf_chunks = []
    video_chunks = []
    
    with open(chunks_file, "r", encoding="utf-8") as f:
        for line in f:
            chk = json.loads(line)
            if lesson_id and lesson_id != "all" and chk.get("lesson_id") != lesson_id:
                continue
            if chk.get("source_type") == "pdf" and "pdf" in allowed_sources:
                pdf_chunks.append(chk)
            elif chk.get("source_type") == "video" and "video" in allowed_sources:
                video_chunks.append(chk)

    if not pdf_chunks and not video_chunks:
        return {
            "status": "NOT_FOUND",
            "reason": "Không có nội dung nào phù hợp với bộ lọc bài học hoặc nguồn đã chọn.",
            "chunks": []
        }

    # Check ambiguity
    if is_query_ambiguous(query):
        return {
            "status": "CLARIFY",
            "reason": "Câu hỏi còn mơ hồ, thiếu đối tượng hoặc ngữ cảnh cụ thể. Bạn vui lòng chỉ rõ khái niệm, số trang slide hoặc đoạn video muốn hỏi.",
            "chunks": []
        }

    # Use dense hybrid search if embeddings are built
    embed_file = repo_root / "materials/derived/embeddings/embeddings.npy"
    if embed_file.exists():
        try:
            from src.vector_store import hybrid_search
            res = hybrid_search(query, lesson_id=lesson_id, allowed_sources=allowed_sources, top_k=top_k)
            if res and res.get("status") == "FOUND":
                return res
        except Exception as e:
            print(f"Hybrid search fallback: {e}")

    results = []

    # If both PDF and Video are allowed, search both independently to ensure dual-source coverage
    if "pdf" in allowed_sources and "video" in allowed_sources and pdf_chunks and video_chunks:
        ret_pdf = BM25Retriever()
        ret_pdf.index(pdf_chunks)
        ranked_pdf = ret_pdf.search(query, top_k=top_k)

        ret_vid = BM25Retriever()
        ret_vid.index(video_chunks)
        ranked_vid = ret_vid.search(query, top_k=top_k)

        for chk, score in ranked_pdf:
            if score >= min_score:
                item = dict(chk)
                item["relevance_score"] = round(score, 3)
                results.append(item)

        for chk, score in ranked_vid:
            if score >= min_score:
                item = dict(chk)
                item["relevance_score"] = round(score, 3)
                results.append(item)
    else:
        all_eligible = pdf_chunks + video_chunks
        retriever = BM25Retriever()
        retriever.index(all_eligible)
        ranked = retriever.search(query, top_k=top_k)
        for chk, score in ranked:
            if score >= min_score:
                item = dict(chk)
                item["relevance_score"] = round(score, 3)
                results.append(item)

    if not results:
        return {
            "status": "NOT_FOUND",
            "reason": "Không tìm thấy nội dung liên quan trong các nguồn bài giảng đã chọn.",
            "chunks": []
        }

    return {
        "status": "FOUND",
        "chunks": results
    }
