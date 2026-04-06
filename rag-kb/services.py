from knowledge_base import KNOWLEDGE_BASE
from schemas import AskResponse


def build_mock_answer(question: str) -> AskResponse:
    for item in KNOWLEDGE_BASE:
        if "fastapi" in question.lower() and "FastAPI" in item:
            return AskResponse(question=question, answer=item)

        if "rag" in question.lower() and "RAG" in item:
            return AskResponse(question=question, answer=item)
    return AskResponse(question=question, answer="暂没找到匹配知识")
