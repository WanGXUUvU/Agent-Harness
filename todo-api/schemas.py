from pydantic import BaseModel


class TodoCreate(BaseModel):
    title: str


class TodoResponse(BaseModel):
    id: int
    title: str


class TodoUpdate(BaseModel):
    title: str
