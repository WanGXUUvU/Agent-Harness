from fastapi import FastAPI
from routes import router
from db import engine,Base
#先让Todos注册到Base上
import models
app = FastAPI()
app.include_router(router)
#旧版数据库连接
#init_db()

Base.metadata.create_all(bind=engine)


