import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from agent_prototype.agent import Agent
from agent_prototype.app import app
from agent_prototype.schemas import AgentInput


class TestAgent(unittest.TestCase):
    @patch("agent_prototype.agent.call_llm", return_value={"role": "assistant", "content": "mock reply"})
    def test_run_updates_state_and_returns_reply(self, mock_call_llm):
        agent = Agent()
        agent_input = AgentInput(session_id="session-a", user_input="你好")

        output = agent.run(agent_input)

        self.assertEqual(output.reply, "mock reply")
        self.assertEqual(output.state.step, 1)
        self.assertEqual(
            [m.model_dump(exclude_none=True) for m in output.state.messages],
            [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "mock reply"},
            ],
        )
        mock_call_llm.assert_called_once()

    @patch(
        "agent_prototype.agent.call_llm",
        side_effect=[
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_001",
                        "type": "function",
                        "function": {
                            "name": "echo_tool",
                            "arguments": "{\"text\": \"hello\"}",
                        },
                    }
                ],
            },
            {"role": "assistant", "content": "final reply"},
        ],
    )
    def test_run_handles_tool_call_then_returns_final_reply(self, mock_call_llm):
        agent = Agent()
        agent_input = AgentInput(session_id="session-a", user_input="帮我测试工具")

        output = agent.run(agent_input)

        self.assertEqual(output.reply, "final reply")
        self.assertEqual(output.state.step, 1)
        self.assertEqual(
            [m.model_dump(exclude_none=True) for m in output.state.messages],
            [
                {"role": "user", "content": "帮我测试工具"},
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_001",
                            "type": "function",
                            "function": {
                                "name": "echo_tool",
                                "arguments": "{\"text\": \"hello\"}",
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "content": "tool received:hello",
                    "tool_call_id": "call_001",
                },
                {"role": "assistant", "content": "final reply"},
            ],
        )
        self.assertEqual(mock_call_llm.call_count, 2)


class TestAgentApi(unittest.TestCase):
    def setUp(self):
        from agent_prototype.routes import session_store

        session_store.clear()
        self.client = TestClient(app)

    @patch("agent_prototype.agent.call_llm", return_value={"role": "assistant", "content": "mock reply"})
    def test_run_endpoint(self, mock_call_llm):
        response = self.client.post("/run", json={"session_id": "session-a", "user_input": "你好"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["reply"], "mock reply")
        self.assertEqual(data["state"]["step"], 1)
        self.assertEqual(
            data["state"]["messages"],
            [
                {"role": "user", "content": "你好", "tool_calls": None, "tool_call_id": None},
                {"role": "assistant", "content": "mock reply", "tool_calls": None, "tool_call_id": None},
            ],
        )
