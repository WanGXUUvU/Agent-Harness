import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agent_prototype.agent import Agent
from agent_prototype.app import app
from agent_prototype.db import Base, get_db
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
        self.assertEqual(
            [e.model_dump(exclude_none=True) for e in output.events],
            [
                {
                    "index": 0,
                    "type": "final_answer",
                    "content": "mock reply",
                }
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
        self.assertEqual(
            [e.model_dump(exclude_none=True) for e in output.events],
            [
                {
                    "index": 0,
                    "type": "assistant_tool_call",
                    "tool_name": "echo_tool",
                    "tool_call_id": "call_001",
                    "content": "{\"text\": \"hello\"}",
                },
                {
                    "index": 1,
                    "type": "tool_result",
                    "tool_name": "echo_tool",
                    "tool_call_id": "call_001",
                    "content": "tool received:hello",
                },
                {
                    "index": 2,
                    "type": "final_answer",
                    "content": "final reply",
                },
            ],
        )
        self.assertEqual(mock_call_llm.call_count, 2)


class TestAgentApi(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "test_agent.db"
        self.engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)

        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()
        self.temp_dir.cleanup()

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
        self.assertEqual(
            data["events"],
            [
                {
                    "index": 0,
                    "type": "final_answer",
                    "content": "mock reply",
                    "tool_name": None,
                    "tool_call_id": None,
                }
            ],
        )
