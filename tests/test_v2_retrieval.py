import unittest

from src.retrieval import evidence_support, is_query_ambiguous, select_evidence
from src.grounded_answer import generate_grounded_answer


def chunk(chunk_id, text, source_type="video"):
    return {
        "chunk_id": chunk_id,
        "source_type": source_type,
        "source_name": "lesson.mp4" if source_type == "video" else "lesson.pdf",
        "source_path": "lesson.mp4" if source_type == "video" else "lesson.pdf",
        "timestamp_label": "00:00 - 00:10",
        "text": text,
    }


class EvidenceGateTests(unittest.TestCase):
    def test_named_short_concepts_are_not_ambiguous(self):
        self.assertFalse(is_query_ambiguous("Token?"))
        self.assertFalse(is_query_ambiguous("ReAct?"))
        self.assertTrue(is_query_ambiguous("cái này dùng sao?"))

    def test_definition_rejects_token_budget_noise(self):
        definition = chunk("definition", "Token là đơn vị nhỏ mà mô hình ngôn ngữ dùng để xử lý văn bản.")
        budget = chunk("budget", "Context window có giới hạn 8192 token và ngân sách đầu ra là 2048 token.")

        self.assertEqual(evidence_support("Token là gì?", definition)["support"], "direct")
        self.assertNotEqual(evidence_support("Token là gì?", budget)["support"], "direct")

    def test_selector_keeps_only_direct_evidence(self):
        candidates = [
            chunk("noise", "Context window có giới hạn 8192 token."),
            chunk("direct", "Token là đơn vị nhỏ dùng để biểu diễn văn bản."),
        ]
        selected = select_evidence("Token là gì?", candidates, max_evidence=3)
        self.assertEqual([item["chunk_id"] for item in selected], ["direct"])
        self.assertEqual(selected[0]["evidence_support"], "direct")

    def test_offline_answer_cites_only_evidence_packet(self):
        direct = chunk("direct", "Token là đơn vị nhỏ dùng để biểu diễn văn bản.")
        result = generate_grounded_answer(
            "Token là gì?",
            {"status": "FOUND", "chunks": [direct]},
            api_key=" ",
        )
        self.assertEqual(result["outcome"], "ANSWER")
        self.assertEqual([citation["chunk_id"] for citation in result["citations"]], ["direct"])


if __name__ == "__main__":
    unittest.main()
