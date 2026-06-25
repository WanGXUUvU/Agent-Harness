import unittest

from backend.prompt.builder import (
    PROMPT_DYNAMIC_BOUNDARY,
    build_runtime_system_prompt,
)
from backend.skills.types import SkillSummary


class TestPromptBuilder(unittest.TestCase):
    def test_build_runtime_system_prompt_orders_sections_by_stability(self):
        prompt = build_runtime_system_prompt(
            available_skills=[
                SkillSummary(
                    name="openai-docs",
                    description="查 OpenAI 官方文档",
                    path="skills/openai-docs/SKILL.md",
                    enabled=True,
                )
            ],
            selected_skill_content="FULL SKILL BODY",
            local_rules_text="workspace rules",
            user_profile_text="user profile",
            agent_overlay_text="agent overlay",
        )

        expected_order = [
            "<AVAILABLE_SKILLS>",
            "<WORKSPACE_RULES>",
            "<USER_PROFILE>",
            "<AGENT_OVERLAY>",
            PROMPT_DYNAMIC_BOUNDARY,
            "<SELECTED_SKILL>",
        ]

        cursor = -1
        for marker in expected_order:
            next_cursor = prompt.find(marker)
            self.assertGreater(next_cursor, cursor)
            cursor = next_cursor

    def test_build_runtime_system_prompt_omits_empty_sections(self):
        prompt = build_runtime_system_prompt(available_skills=[])

        self.assertEqual(prompt, "")


if __name__ == "__main__":
    unittest.main()
