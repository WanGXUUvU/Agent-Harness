# todo-api

一个用于练习 `FastAPI` 后端基础的最小 CRUD 项目。

当前项目重点：
- 熟悉 `GET / POST / PUT / DELETE`
- 练习请求体、路径参数、响应模型
- 练习 `HTTPException` 和常见状态码
- 练习最小项目结构拆分
- 理解本地 `JSON` 持久化和 SQLite 数据库存储的区别
- 理解路由层、服务层、数据层的基本分工

## 当前功能

已实现接口：
- `GET /`
- `GET /health`
- `GET /todos`
- `GET /todos/{todo_id}`
- `POST /todos`
- `PUT /todos/{todo_id}`
- `DELETE /todos/{todo_id}`

## 请求与响应

创建 todo 请求体：

```json
{
  "title": "学习 FastAPI"
}
```

单条 todo 响应：

```json
{
  "id": 1,
  "title": "学习 FastAPI"
}
```

## 项目结构

```text
todo-api/
├── app.py
├── db.py
├── routes.py
├── schemas.py
├── services.py
├── data.py
├── todo.db
├── todos.json
└── README.md
```

文件职责：
- `app.py`：应用入口，创建 `FastAPI` 实例并注册路由
- `db.py`：SQLite 连接和建表初始化
- `routes.py`：接口定义，接收请求并调用服务函数
- `schemas.py`：请求体和响应体模型
- `services.py`：CRUD 业务逻辑
- `data.py`：旧版 `JSON` 持久化逻辑
- `todo.db`：当前练手项目使用的 SQLite 数据库文件
- `todos.json`：上一阶段的本地 JSON 数据文件，当前已不是主存储

## 如何启动

在项目目录下执行：

```bash
cd "/Users/wangxu/Documents/RAG 检索知识库/todo-api"
source .venv/bin/activate
uvicorn app:app --reload
```

启动后可访问：
- `http://127.0.0.1:8000/docs`

## 如何测试

查询健康状态：

```bash
curl "http://127.0.0.1:8000/health"
```

新增一条 todo：

```bash
curl -X POST "http://127.0.0.1:8000/todos" \
  -H "Content-Type: application/json" \
  -d '{"title":"学习 FastAPI"}'
```

查询全部 todo：

```bash
curl "http://127.0.0.1:8000/todos"
```

查询单条 todo：

```bash
curl "http://127.0.0.1:8000/todos/1"
```

修改 todo：

```bash
curl -X PUT "http://127.0.0.1:8000/todos/1" \
  -H "Content-Type: application/json" \
  -d '{"title":"学习 PUT 修改"}'
```

删除 todo：

```bash
curl -X DELETE "http://127.0.0.1:8000/todos/1"
```

## 当前学习收获

通过这个项目，已经练到：
- 使用 `FastAPI` 搭建最小后端服务
- 编写 CRUD 接口
- 使用 `BaseModel` 定义请求和响应结构
- 使用 `response_model` 约束返回格式
- 使用 `HTTPException` 处理查不到数据的情况
- 使用本地 `JSON` 文件做最小持久化
- 将部分 CRUD 逻辑拆到 `services.py`
- 为 `load_todos()` 增加最小异常处理
- 使用 `sqlite3` 连接 SQLite 数据库
- 使用 SQL 完成基础查询与插入
- 理解 `db.py`、`services.py`、`routes.py` 的协作方式

## 当前限制

当前项目仍是后端基础练手版本：
- 项目正在从 `JSON` 存储迁移到 `SQLite`
- 目前数据库版 CRUD 处于迁移过程中，部分旧逻辑仍可继续清理
- 还没有用户系统、认证、分页、日志等能力
- 还没有引入 ORM 或 SQL 查询

## 下一步

后续准备继续补这些能力：
- 完成 `todo-api` 的 SQLite 版 CRUD 收口
- 继续熟悉 SQL 在 Python 后端里的使用
- 后续再从 `sqlite3` 过渡到更标准的数据库访问方式
- 后续再把这些后端基础迁移到 RAG 项目里
