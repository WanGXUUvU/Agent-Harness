import unittest

from backend.prompt.compaction import (
    extract_compact_summary,
    HistoryCompactor,
)
from backend.core.types import ChatMessage, ModelResponse, ModelUsage


class TestCompaction(unittest.TestCase):
    def test_extract_compact_summary_prefers_summary_tag(self):
        raw_output = (
            "<analysis>internal reasoning should not be persisted</analysis>\n"
            "<summary>final structured summary</summary>"
        )

        self.assertEqual(
            extract_compact_summary(raw_output), "final structured summary"
        )

    def test_history_compactor_returns_compacted_messages(self):
        class FakeAdapter:
            def generate(self, request):
                self.request = request
                return ModelResponse(
                    assistant_message=ChatMessage(
                        role="assistant",
                        content=(
                            "<analysis>internal reasoning should not be persisted</analysis>"
                            "<summary>compressed summary</summary>"
                        ),
                    ),
                    usage=ModelUsage(input_tokens=12, output_tokens=4, total_tokens=16),
                )

        adapter = FakeAdapter()
        compactor = HistoryCompactor(adapter)

        result = compactor.compact_messages(
            [
                ChatMessage(role="user", content="old user"),
                ChatMessage(role="assistant", content="old assistant"),
            ]
        )

        self.assertEqual(result.compact_tokens, 12)
        self.assertEqual(len(result.messages), 1)
        self.assertEqual(result.messages[0].role, "system")
        self.assertIn("[COMPACT_SUMMARY]", result.messages[0].content)
        self.assertIn("compressed summary", result.messages[0].content)
        self.assertNotIn("internal reasoning", result.messages[0].content)
        self.assertFalse(adapter.request.config.stream)
