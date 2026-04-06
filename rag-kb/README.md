# rag-kb

一个用于学习 `FastAPI` 和后续实现 `RAG 知识库问答系统` 的练手项目。

## 1. 项目目标

当前目标：
- 学习 `FastAPI` 基本用法
- 理解 `GET`、`POST`、查询参数、请求体
- 搭建后续 `RAG` 项目的最小后端骨架

## 2. 当前功能

目前已实现接口：
- `GET /`
- `GET /health`
- `GET /hello`
- `GET /greet?name=xxx`
- `POST /echo`

## 3. 项目结构

```text
rag-kb/
├── app.py
├── routes.py
├── schemas.py
└── README.md
```

- app.py：应用入口，创建 FastAPI 实例
- routes.py：定义所有接口
- schemas.py：定义请求体数据模型
## 4.如何启动
```
uv venv --python 3.12
source .venv/bin/activate
uv pip install fastapi uvicorn
uvicorn app:app --reload

```
## 5.学习收获
- FastAPI 最小项目如何启动
- GET 和 POST 的基本区别
- 查询参数的基本写法
- BaseModel 用于定义请求体格式
- 简单后端项目如何拆分文件