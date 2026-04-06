from fastapi import APIRouter

from schemas import AskRequest, EchoRequest
from services import build_mock_answer

router = APIRouter()


@router.get("/")
def read_root():
    return {"message": "hello world"}


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/hello")
def say_hello():
    return {"message": "hello,wangxu"}


@router.get("/greet")
def greet(name: str):
    return {"message": f"hello,{name}"}


@router.post("/echo")
def echo(request: EchoRequest):
    return {"message": request}


@router.post("/ask")
def ask(request: AskRequest):
    return build_mock_answer(request.question)
