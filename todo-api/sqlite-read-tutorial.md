# 1 小时离线教程：把 todo-api 的读取接口迁移到 SQLite

## 教程目标

这一小时只做一件事：

**把 `todo-api` 的读取逻辑，从内存 / JSON 方式，迁移到 SQLite 查询。**

你这次不要同时改全部 CRUD。  
只先改两个读取接口：

- `GET /todos`
- `GET /todos/{todo_id}`

这样最稳，也最容易看懂。

## 本小时学完你应该会的东西

你应该能说清楚这几件事：

- `services.py` 怎么调用 `db.py`
- `SELECT` 查询结果怎么变成接口返回值
- `fetchall()` 和 `fetchone()` 的区别
- 为什么读取逻辑可以先迁到数据库，而新增/修改/删除先不动

## 当前建议的文件分工

这一小时你主要会碰这两个文件：

- `db.py`：数据库连接与建表
- `services.py`：数据库查询逻辑

你可能还会动：

- `routes.py`：把读取接口改成调用新的服务函数

## 第一部分：先迁移 `GET /todos`

### 1. 先写数据库版 `get_all_todos()`

在 [services.py](/Users/wangxu/Documents/RAG%20检索知识库/todo-api/services.py) 里增加这个导入：

```python
from db import get_connection
```

然后写：

```python
def get_all_todos():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, title FROM todos")
    rows = cursor.fetchall()

    conn.close()

    return [
        {"id": row["id"], "title": row["title"]}
        for row in rows
    ]
```

### 2. 逐行解释这段代码

#### `conn = get_connection()`

```python
conn = get_connection()
```

作用：

- 拿到数据库连接
- 后面所有 SQL 查询都要靠它

你可以理解成：

**先连上数据库，再谈查询。**

#### `cursor = conn.cursor()`

```python
cursor = conn.cursor()
```

作用：

- 拿游标
- 用它执行 SQL

你可以理解成：

**连接是通道，游标是操作 SQL 的手。**

#### `cursor.execute("SELECT id, title FROM todos")`

```python
cursor.execute("SELECT id, title FROM todos")
```

作用：

- 执行查询 SQL
- 从 `todos` 表里查所有 todo 的 `id` 和 `title`

这句 SQL 的含义：

```sql
SELECT id, title FROM todos
```

翻译成人话：

**把 `todos` 表里的 `id` 和 `title` 两列全部查出来。**

#### `rows = cursor.fetchall()`

```python
rows = cursor.fetchall()
```

作用：

- 把查询结果全部取出来

如果数据库里有三条数据，它大概就是：

```python
[
    row1,
    row2,
    row3
]
```

每个 `row` 因为设置了 `sqlite3.Row`，所以能按列名取值。

#### `conn.close()`

```python
conn.close()
```

作用：

- 查询完成后关闭连接

习惯上：

- 用完数据库连接就关
- 不要一直挂着

#### 返回值转换

```python
return [
    {"id": row["id"], "title": row["title"]}
    for row in rows
]
```

作用：

- 把数据库查出来的每一行
- 变成普通字典
- 再组成一个列表返回

为什么要这么做？

因为 FastAPI 最终更适合返回这种结构：

```python
[
    {"id": 1, "title": "学习 FastAPI"},
    {"id": 2, "title": "学习 CRUD"}
]
```

### 3. 把 `GET /todos` 路由接过来

在 [routes.py](/Users/wangxu/Documents/RAG%20检索知识库/todo-api/routes.py) 顶部导入：

```python
from services import get_all_todos
```

然后把这段：

```python
@router.get("/todos", response_model=list[TodoResponse])
def get_todos():
    return TODOS
```

改成：

```python
@router.get("/todos", response_model=list[TodoResponse])
def get_todos():
    return get_all_todos()
```

### 4. 你现在应该怎么理解

这一步的分工是：

- `routes.py`：有人访问 `/todos` 时，调用服务函数
- `services.py`：去数据库查数据
- `db.py`：提供数据库连接

你现在应该能用一句话说：

**路由层不直接写 SQL，SQL 放在服务层里。**

## 第二部分：再迁移 `GET /todos/{todo_id}`

### 5. 写数据库版按 id 查询函数

在 [services.py](/Users/wangxu/Documents/RAG%20检索知识库/todo-api/services.py) 里加：

```python
def get_todo_by_id(todo_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, title FROM todos WHERE id = ?",
        (todo_id,)
    )
    row = cursor.fetchone()

    conn.close()

    if row is None:
        return None

    return {"id": row["id"], "title": row["title"]}
```

### 6. 逐行解释新东西

#### `WHERE id = ?`

```python
"SELECT id, title FROM todos WHERE id = ?"
```

作用：

- 只查一条符合条件的数据
- 这里条件是 `id = ?`

这相当于 SQL：

```sql
SELECT id, title FROM todos WHERE id = 1
```

但这里没有直接把值写死，而是用占位符 `?`。

#### `(todo_id,)`

```python
(todo_id,)
```

作用：

- 把真正的参数值传给 SQL

为什么是这种写法？

因为 `sqlite3` 里参数化 SQL 常用这种形式。  
即使只有一个参数，也要写成元组：

```python
(todo_id,)
```

注意最后那个逗号不能少。

#### `cursor.fetchone()`

```python
row = cursor.fetchone()
```

作用：

- 只取一条结果

和 `fetchall()` 区别：

- `fetchall()`：取全部
- `fetchone()`：只取一条

因为按 `id` 查 todo，正常只会有一条或没有。

#### `if row is None`

```python
if row is None:
    return None
```

作用：

- 如果数据库里没有这条数据
- 返回 `None`

然后路由层再根据 `None` 决定要不要抛 `404`

这就是职责分工：

- 服务层：告诉你“有没有查到”
- 路由层：决定 HTTP 怎么响应

### 7. 改路由

在 [routes.py](/Users/wangxu/Documents/RAG%20检索知识库/todo-api/routes.py) 里，保留这种结构：

```python
@router.get("/todos/{todo_id}", response_model=TodoResponse)
def get_todo(todo_id: int):
    todo = get_todo_by_id(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo
```

这一步如果你已经有同名函数，记得保证导入的是数据库版那个。

## 第三部分：为什么这一步先迁移“读”，不先迁移“写”

这是非常重要的工程节奏。

因为读取接口更适合先迁移：

- 风险低
- 没有写入副作用
- 容易验证结果
- 有助于你先把查询逻辑搞明白

如果你一开始就迁移：

- `POST`
- `PUT`
- `DELETE`

那你会同时碰到：

- SQL 插入
- SQL 更新
- SQL 删除
- 提交事务

一下会太多。

所以现在先迁移 `GET` 是正确顺序。

## 第四部分：本小时练习安排

### 0-10 分钟

不看教程，自己默写数据库版 `get_all_todos()`。

目标：

- 写出 `get_connection()`
- 写出 `cursor.execute(...)`
- 写出 `fetchall()`
- 写出列表转换

### 10-20 分钟

把 `GET /todos` 真正接到数据库查询函数上。

你要确认自己能回答：

- 为什么这里不再返回 `TODOS`
- 为什么要调用 `get_all_todos()`

### 20-35 分钟

自己写 `get_todo_by_id(todo_id: int)`。

重点理解：

- `WHERE id = ?`
- `(todo_id,)`
- `fetchone()`
- `if row is None`

### 35-45 分钟

把 `GET /todos/{todo_id}` 路由改成调用数据库服务函数。

你要自己解释：

- 为什么 `404` 放在路由层
- 为什么 `None` 可以作为“没查到”的信号

### 45-55 分钟

纸面回答这 5 个问题：

1. `fetchall()` 和 `fetchone()` 有什么区别  
2. 为什么 SQL 里要写 `WHERE id = ?`  
3. 为什么参数写成 `(todo_id,)`  
4. 为什么查询后要 `conn.close()`  
5. 为什么读取逻辑更适合先迁移到数据库

### 55-60 分钟

自己写一句总结：

**今天我学会了如何让 FastAPI 的读取接口从 SQLite 查数据，而不是从内存列表取数据。**

## 第五部分：你现在必须会的两段代码

### 数据库版查全部

```python
def get_all_todos():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, title FROM todos")
    rows = cursor.fetchall()

    conn.close()

    return [
        {"id": row["id"], "title": row["title"]}
        for row in rows
    ]
```

### 数据库版查单条

```python
def get_todo_by_id(todo_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, title FROM todos WHERE id = ?",
        (todo_id,)
    )
    row = cursor.fetchone()

    conn.close()

    if row is None:
        return None

    return {"id": row["id"], "title": row["title"]}
```

## 第六部分：这一小时结束后的判断标准

如果你能做到下面 4 条，就算学成：

- 能写出数据库版 `get_all_todos()`
- 能写出数据库版 `get_todo_by_id()`
- 能解释 `fetchall()` / `fetchone()` 的区别
- 能解释 `WHERE id = ?` 和 `(todo_id,)` 的作用

## 下一步预告

等这一步你吃透后，下一阶段最自然的就是：

**把 `POST /todos` 迁移到 SQLite 插入。**

也就是你会开始接触：

- `INSERT INTO`
- `commit()`
- 新增后如何拿到数据库生成的 id
