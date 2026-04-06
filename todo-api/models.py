from sqlalchemy import Column,Integer,String

from db import Base

class Todo(Base):
    __tablename__="todos"

    id=Column(Integer,primary_key=True,index=True)
    title=Column(String,nullable=False)