import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from agent_prototype.agent import Agent
from agent_prototype.app import app
from agent_prototype.schemas import AgentInput


class TestAgent(unittest.TestCase):
    @patch("agent_prototype.agent.call_llm", return_value="mock reply")
    def test_run_updates_state_and_returns_reply(self, mock_call_llm):
        agent = Agent()
        agent_input = AgentInput(user_input="你好")

        output = agent.run(agent_input)

        self.assertEqual(output.reply, "mock reply")
        self.assertEqual(output.state.step, 1)
        self.assertEqual(
            [m.model_dump() for m in output.state.messages],
            [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "mock reply"},
            ],
        )
        mock_call_llm.assert_called_once()


class TestAgentApi(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("agent_prototype.agent.call_llm", return_value="mock reply")
    def test_run_endpoint(self, mock_call_llm):
        response = self.client.post("/run", json={"user_input": "你好"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["reply"], "mock reply")
        self.assertEqual(data["state"]["step"], 1)
        self.assertEqual(
            data["state"]["messages"],
            [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "mock reply"},
            ],
        )
