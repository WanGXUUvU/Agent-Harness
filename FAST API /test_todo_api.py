import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import app
from db import Base, get_db


class TodoApiTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "test_todo.db"
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=self.engine)
        TestingSessionLocal = sessionmaker(
            autoflush=False,
            autocommit=False,
            bind=self.engine,
        )

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

    def create_todo(self, title="学习测试", done=False, priority=1):
        response = self.client.post(
            "/todos",
            json={"title": title, "done": done, "priority": priority},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_delete_then_get_returns_404(self):
        created_todo = self.create_todo()
        todo_id = created_todo["id"]

        delete_response = self.client.delete(f"/todos/{todo_id}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json()["id"], todo_id)

        get_response = self.client.get(f"/todos/{todo_id}")
        self.assertEqual(get_response.status_code, 404)

    def test_patch_title_only_keeps_other_fields_unchanged(self):
        created_todo = self.create_todo(title="原始标题", done=False, priority=1)
        todo_id = created_todo["id"]

        patch_response = self.client.patch(
            f"/todos/{todo_id}",
            json={"title": "新标题"},
        )

        self.assertEqual(patch_response.status_code, 200)
        patched_todo = patch_response.json()
        self.assertEqual(patched_todo["id"], todo_id)
        self.assertEqual(patched_todo["title"], "新标题")
        self.assertEqual(patched_todo["done"], False)
        self.assertEqual(patched_todo["priority"], 1)

    def test_patch_empty_body_returns_400(self):
        created_todo = self.create_todo()
        todo_id = created_todo["id"]

        patch_response = self.client.patch(f"/todos/{todo_id}", json={})

        self.assertEqual(patch_response.status_code, 400)
        self.assertEqual(patch_response.json()["detail"], "No fields provided for update")

    def test_patch_missing_todo_returns_404(self):
        patch_response = self.client.patch(
            "/todos/999999",
            json={"title": "不存在的任务"},
        )

        self.assertEqual(patch_response.status_code, 404)
        self.assertEqual(patch_response.json()["detail"], "Todo not found")

    def test_patch_false_value_is_preserved(self):
        created_todo = self.create_todo(done=True)
        todo_id = created_todo["id"]

        patch_response = self.client.patch(
            f"/todos/{todo_id}",
            json={"done": False},
        )

        self.assertEqual(patch_response.status_code, 200)
        patched_todo = patch_response.json()
        self.assertEqual(patched_todo["id"], todo_id)
        self.assertEqual(patched_todo["done"], False)
        self.assertEqual(patched_todo["title"], "学习测试")
        self.assertEqual(patched_todo["priority"], 1)


if __name__ == "__main__":
    unittest.main()
