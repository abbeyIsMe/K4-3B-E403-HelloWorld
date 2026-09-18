"""Deterministic follow-up query resolution for the lecture chat."""

from src.retrieval import is_query_ambiguous, query_anchors


def _subject_from_turn(turn: dict) -> str | None:
    result = turn.get("result", {})
    if result.get("outcome") != "ANSWER":
        return None
    query = turn.get("resolved_query") or turn.get("query", "")
    anchors = query_anchors(query)
    return anchors[0] if anchors else None


def resolve_query(query: str, chat_history: list[dict] | None = None) -> dict:
    """Resolve a follow-up from the latest grounded subject without guessing."""
    clean_query = query.strip()
    if not clean_query:
        return {"status": "CLARIFY", "query": "", "reason": "Câu hỏi đang trống."}

    if not is_query_ambiguous(clean_query):
        return {"status": "READY", "query": clean_query, "used_context": False}

    for turn in reversed(chat_history or []):
        subject = _subject_from_turn(turn)
        if subject:
            return {
                "status": "READY",
                "query": f"{subject}: {clean_query}",
                "used_context": True,
                "subject": subject,
            }

    return {
        "status": "CLARIFY",
        "query": clean_query,
        "used_context": False,
        "reason": "Câu hỏi tiếp nối nhưng chưa có khái niệm nào từ lượt trước để tham chiếu. Vui lòng nêu rõ chủ đề.",
    }
