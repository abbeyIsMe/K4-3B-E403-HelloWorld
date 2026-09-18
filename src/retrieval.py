import re
import math
import json
from pathlib import Path
from collections import Counter

KNOWN_ENTITIES = (
    "token", "tokenizer", "react", "rag", "agent", "embedding", "hallucination",
    "context window", "system prompt", "tool calling", "function calling",
    "double diamond", "poc canvas", "json schema", "python", "fine-tuning", "temperature", "top_p",
    "few-shot", "zero-shot"
)

DEFINITION_MARKERS = (
    "là", "được gọi là", "định nghĩa", "khái niệm", "có nghĩa là", "đơn vị",
    "đóng vai trò", "dùng để", "là cách"
)

CALCULATION_MARKERS = (
    "tính", "bao nhiêu", "giới hạn", "ngân sách", "chi phí", "có thể", "còn lại"
)

OUT_OF_SCOPE_PATTERNS = (
    "bỏ qua toàn bộ hướng dẫn",
    "trả lời ngoài bài giảng",
    "tấn công server",
    "viết code tấn công",
    "cách làm bánh pizza",
)

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


def analyze_query(query: str) -> dict:
    """Extract only stable query signals used by the evidence gate."""
    q = query.lower().strip()
    entities = [entity for entity in KNOWN_ENTITIES if entity in q]
    if any(marker in q for marker in ("quy trình", "các bước", "làm sao", "cách", "hoạt động ra sao")):
        intent = "procedure"
    elif any(marker in q for marker in ("là gì", "khái niệm", "định nghĩa", "thế nào là", "ý nghĩa")):
        intent = "definition"
    elif any(marker in q for marker in CALCULATION_MARKERS):
        intent = "calculation"
    elif any(marker in q for marker in ("so sánh", "khác nhau", "giống nhau")):
        intent = "comparison"
    elif entities and len(BM25Retriever.tokenize(query, remove_stopwords=True)) <= 2:
        intent = "definition"
    else:
        intent = "lookup"
    return {"intent": intent, "entities": entities}


def _content_tokens(text: str) -> set[str]:
    return set(BM25Retriever.tokenize(text, remove_stopwords=True))


def evidence_support(query: str, chunk: dict) -> dict:
    """Classify whether a candidate directly supports the user's whole question.

    This is intentionally conservative. A keyword hit is only partial evidence;
    definition questions require a definition-shaped sentence, and calculation
    questions require calculation/constraint language in the same chunk.
    """
    q = query.lower().strip()
    text = chunk.get("text", "").lower()
    signals = analyze_query(query)
    q_terms = _content_tokens(query)
    text_terms = _content_tokens(text)
    entities = signals["entities"]
    overlap = q_terms & text_terms
    lexical_ratio = len(overlap) / max(1, len(q_terms))
    entity_hit = any(entity in text for entity in entities)
    definition_hit = entity_hit and any(
        re.search(
            rf"{re.escape(entity)}\s+(?:là|được gọi là|có nghĩa là|đóng vai trò|dùng để|là cách)",
            text,
        )
            or re.search(rf"(?:định nghĩa|khái niệm|được gọi là)\s+(?:về\s+)?{re.escape(entity)}", text)
            or re.search(rf"đơn vị[^.\n]{{0,80}}được gọi là\s+{re.escape(entity)}", text)
            or (
                entity == "json schema"
                and re.search(rf"{re.escape(entity)}[^.\n]{{0,50}}\blà\b", text)
            )
            or re.search(rf"{re.escape(entity)}\s*=", text)
        for entity in entities
    )
    calculation_hit = entity_hit and (
        any(marker in text for marker in CALCULATION_MARKERS)
        or bool(re.search(r"\d+(?:[.,]\d+)?\s*(?:token|%|giây|phút|trang)", text))
    )
    if re.search(r"\bmodel\s+a\b", q) and not re.search(r"\bmodel\s+a\b", text):
        calculation_hit = False

    if not overlap and not entity_hit:
        return {"support": "none", "score": 0.0, "reason": "Không có thực thể hoặc thuật ngữ của câu hỏi."}

    intent = signals["intent"]
    if intent == "definition":
        if definition_hit:
            return {"support": "direct", "score": round(0.75 + min(0.2, lexical_ratio), 3), "reason": "Có thực thể và câu mô tả định nghĩa."}
        return {"support": "partial", "score": round(0.25 + min(0.25, lexical_ratio), 3), "reason": "Có thuật ngữ nhưng không có mô tả định nghĩa."}

    if intent == "calculation":
        if calculation_hit and lexical_ratio >= 0.25:
            return {"support": "direct", "score": round(0.65 + min(0.3, lexical_ratio), 3), "reason": "Có thuật ngữ cùng ràng buộc hoặc phép tính liên quan."}
        return {"support": "partial", "score": round(min(0.45, lexical_ratio), 3), "reason": "Có thuật ngữ nhưng thiếu dữ kiện tính toán."}

    if lexical_ratio >= 0.60 or (entity_hit and lexical_ratio >= 0.25):
        return {"support": "direct", "score": round(0.45 + min(0.5, lexical_ratio), 3), "reason": "Các thuật ngữ chính của câu hỏi cùng xuất hiện trong evidence."}
    return {"support": "partial", "score": round(lexical_ratio, 3), "reason": "Chỉ khớp một phần thuật ngữ."}


def select_evidence(query: str, candidates: list[dict], max_evidence: int = 5) -> list[dict]:
    """Return only direct evidence, preserving relevance order and source diversity."""
    ranked = []
    for position, candidate in enumerate(candidates):
        item = dict(candidate)
        support = evidence_support(query, item)
        item.update({f"evidence_{key}": value for key, value in support.items()})
        item["_position"] = position
        ranked.append(item)

    ranked.sort(key=lambda item: (-item["evidence_score"], item["_position"]))
    selected = [item for item in ranked if item["evidence_support"] == "direct"][:max_evidence]
    for item in selected:
        item.pop("_position", None)
    return selected


def is_query_ambiguous(query: str) -> bool:
    """Detect if question is too vague, generic, or lacks substantive context."""
    q = query.strip().lower()
    clean = re.sub(r"[^\w\s]", "", q)
    words = clean.split()
    
    if len(words) <= 2:
        # Short named concepts such as "Token?" and "ReAct?" are valid
        # definition questions; only unknown short phrases need clarification.
        if any(entity in q for entity in KNOWN_ENTITIES):
            return False
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


def is_explicitly_out_of_scope(query: str) -> bool:
    q = query.lower().strip()
    return any(pattern in q for pattern in OUT_OF_SCOPE_PATTERNS)


def bm25_candidates(query: str, chunks: list[dict], top_k: int = 24, min_score: float = 0.0) -> list[dict]:
    """Offline candidate retrieval used both directly and by vector fallback."""
    retriever = BM25Retriever()
    retriever.index(chunks)
    return [
        {**chk, "relevance_score": round(score, 3)}
        for chk, score in retriever.search(query, top_k=top_k)
        if score >= min_score
    ]


def retrieve_evidence(query: str, lesson_id="all", allowed_sources=None, top_k=3, min_score=0.0, use_dense=True):
    """
    Retrieve candidate chunks with dual-source balancing (PDF and Video).
    top_k: Number of top chunks per source type (e.g. 3 PDF + 3 Video).
    """
    if allowed_sources is None:
        allowed_sources = ["pdf", "video"]

    if is_explicitly_out_of_scope(query):
        return {
            "status": "NOT_FOUND",
            "reason": "Câu hỏi nằm ngoài phạm vi nội dung bài giảng.",
            "chunks": []
        }
        
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

    # Use a larger candidate pool, then apply a direct-evidence gate. The old
    # implementation forced one quota for each source and sent weak chunks on.
    candidate_limit = max(12, top_k * 4)
    embed_file = repo_root / "materials/derived/embeddings/embeddings.npy"
    if use_dense and embed_file.exists():
        try:
            from src.vector_store import hybrid_search
            res = hybrid_search(query, lesson_id=lesson_id, allowed_sources=allowed_sources, top_k=candidate_limit)
            if res and res.get("status") == "FOUND":
                selected = select_evidence(query, res.get("chunks", []), max_evidence=top_k)
                if selected:
                    return {"status": "FOUND", "chunks": selected, "candidate_count": len(res.get("chunks", []))}
                return {
                    "status": "NOT_FOUND",
                    "reason": "Có kết quả gần về từ khóa nhưng không đủ bằng chứng trực tiếp để trả lời câu hỏi.",
                    "chunks": [],
                    "candidate_count": len(res.get("chunks", []))
                }
        except Exception as e:
            print(f"Hybrid search fallback: {e}")

    results = bm25_candidates(query, pdf_chunks + video_chunks, candidate_limit, min_score)
    results = select_evidence(query, results, max_evidence=top_k)

    if not results:
        return {
            "status": "NOT_FOUND",
            "reason": "Không tìm thấy bằng chứng trực tiếp trong các nguồn bài giảng đã chọn.",
            "chunks": []
        }

    return {
        "status": "FOUND",
        "chunks": results
    }
