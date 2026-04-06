from models import Todo
from db import SessionLocal

# def get_all_todos():
#     conn=get_connection()
#     cursor=conn.cursor()

#     cursor.execute("SELECT id,title FROM todos")
#     rows=cursor.fetchall()
    
#     conn.close()

#     return [
#         {"id":row["id"],"title":row["title"]}
#         for row in rows
#     ]
def get_all_todos():
    db=SessionLocal()

    todos=db.query(Todo).all()

    db.close()

    return [{"id":todo.id,"title":todo.title}
            for todo in todos
    
    ]

def get_todo_by_id(todo_id):
    conn=get_connection()
    cursor=conn.cursor()

    cursor.execute("SELECT id,title FROM todos where id=?",(todo_id,))
    row=cursor.fetchone()
    conn.close()

    if row==None:return None

    return{"id":row["id"],"title":row["title"]}

##新增一个todo
def create_todo(title:str):
    conn=get_connection()
    cursor=conn.cursor()
    cursor.execute("INSERT INTO todos (title) VALUES (?)",(title,))

    conn.commit()
    
    new_id=cursor.lastrowid
    conn.close()
    return{"id":new_id,"title":title}
    
    
##删除一个todo
def delete_todo(todo_id:int):
    todo=get_todo_by_id(todo_id)
    if todo is None:return None
    conn=get_connection()
    cursor=conn.cursor()

    cursor.execute("DELETE  from todos where id=?",(todo_id,))

    conn.commit()
    
    conn.close()
    return todo

def update_todo(todo_id:int,title:str):
    conn=get_connection()
    cursor=conn.cursor()

    cursor.execute("UPDATE todos set title = ? where id=?",(title,todo_id,))

    conn.commit()
    
    if cursor.rowcount==0:
        conn.close()
        return None

    conn.close()

    return {"id":todo_id,"title":title}