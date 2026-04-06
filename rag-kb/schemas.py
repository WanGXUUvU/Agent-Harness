from pydantic import BaseModel


class EchoRequest(BaseModel):
    text: str


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    question: str
    answer: str
