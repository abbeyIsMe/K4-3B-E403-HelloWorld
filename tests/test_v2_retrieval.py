import unittest

from src.retrieval import evidence_support, is_query_ambiguous, normalize_query, select_evidence
from src.grounded_answer import _evidence_fallback, generate_grounded_answer
from src.query_context import resolve_query


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

    def test_unaccented_definition_keeps_source_filter_gate(self):
        budget = chunk(
            "budget",
            "Context window có giới hạn 8192 token và ngân sách đầu ra là 2048 token.",
            source_type="pdf",
        )
        selected = select_evidence("Token la gi?", [budget])
        self.assertEqual(selected, [])

    def test_pronoun_and_followup_queries_need_context(self):
        self.assertTrue(is_query_ambiguous("Nó hoạt động thế nào?"))
        self.assertTrue(is_query_ambiguous("Còn nhược điểm thì sao?"))
        self.assertTrue(is_query_ambiguous("Cho ví dụ đi"))

    def test_followup_uses_latest_grounded_subject(self):
        history = [{
            "query": "PII là gì?",
            "resolved_query": "PII là gì?",
            "result": {"outcome": "ANSWER"},
        }]
        resolved = resolve_query("Còn nhược điểm thì sao?", history)
        self.assertEqual(resolved["status"], "READY")
        self.assertEqual(resolved["query"], "pii: Còn nhược điểm thì sao?")
        self.assertTrue(resolved["used_context"])

    def test_followup_without_grounded_subject_stays_clarify(self):
        resolved = resolve_query("Còn nhược điểm thì sao?", [{
            "query": "Giải thích đi",
            "result": {"outcome": "CLARIFY"},
        }])
        self.assertEqual(resolved["status"], "CLARIFY")

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

    def test_contextual_term_is_supported_by_related_source_context(self):
        pii_context = chunk(
            "pii-context",
            "Privacy: Có PII hoặc dữ liệu nhạy cảm không? Cần masking và access control.",
            source_type="pdf",
        )
        unrelated = chunk("unrelated", "Context window có giới hạn 8192 token.", source_type="pdf")

        self.assertEqual(evidence_support("PII là gì?", pii_context)["support"], "contextual")
        self.assertNotEqual(evidence_support("PII là gì?", unrelated)["support"], "direct")

    def test_few_shot_spacing_variant_matches_hyphenated_source(self):
        self.assertEqual(normalize_query("Few shot là gì?"), "few-shot là gì?")
        evidence = chunk(
            "few-shot-fixture",
            "Few-shot là cách cung cấp một vài ví dụ để hướng dẫn mô hình.",
            source_type="pdf",
        )
        selected = select_evidence("Few shot là gì?", [evidence])
        self.assertEqual([item["chunk_id"] for item in selected], ["few-shot-fixture"])

    def test_offline_answer_cites_only_evidence_packet(self):
        direct = chunk("direct", "Token là đơn vị nhỏ dùng để biểu diễn văn bản.")
        result = generate_grounded_answer(
            "Token là gì?",
            {"status": "FOUND", "chunks": [direct]},
            api_key=" ",
        )
        self.assertEqual(result["outcome"], "ANSWER")
        self.assertEqual([citation["chunk_id"] for citation in result["citations"]], ["direct"])

    def test_contextual_fallback_is_answer_with_real_citations(self):
        pii = chunk(
            "pii-context",
            "Privacy cần xác định có PII hoặc dữ liệu nhạy cảm không và áp dụng masking.",
            source_type="pdf",
        )
        result = _evidence_fallback([pii])
        self.assertEqual(result["outcome"], "ANSWER")
        self.assertIn("chưa đưa ra định nghĩa đầy đủ", result["answer"])
        self.assertIn("[cite:pii-context]", result["answer"])
        self.assertEqual(result["citations"][0]["chunk_id"], "pii-context")


if __name__ == "__main__":
    unittest.main()
