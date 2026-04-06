from fastapi import APIRouter, HTTPException

from schemas import TodoCreate, TodoResponse, TodoUpdate
from services import get_todo_by_id,create_todo,update_todo,delete_todo
from services import get_all_todos
router = APIRouter()


@router.get("/")
def read_root():
    return {"message": "hello world"}


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.get("/todos", response_model=list[TodoResponse])
def get_todos():
    return get_all_todos()


@router.get("/todos/{todo_id}", response_model=TodoResponse)
def get_todo(todo_id: int):
    todo=get_todo_by_id(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.post("/todos", response_model=TodoResponse, status_code=201)
def create_todos_api(request: TodoCreate):
    return create_todo(request.title)


@router.delete("/todos/{todo_id}")
def delete_todo_api(todo_id: int):
    todo=delete_todo(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.put("/todos/{todo_id}")
def update_todo_api(todo_id: int, request: TodoUpdate):
    todo=update_todo(todo_id,request.title)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo
