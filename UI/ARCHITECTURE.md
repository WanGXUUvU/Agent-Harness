# 系统架构与功能链路文档

> 最后更新：2026-05-17

---

## 项目层次总览

```
┌─────────────────────────────────────────────────────────┐
│                     HTTP 入口层                          │
│                  api/routes/                             │
│  run_routes.py   trace_routes.py   session_routes.py    │
└──────────────────────┬──────────────────────────────────┘
                       │ 调用
┌──────────────────────▼──────────────────────────────────┐
│                    应用服务层                            │
│                  application/                            │
│  run_service.py          session_service.py             │
│  compact_service.py      skill_service.py               │
│  agent_definition_service.py  skill_context_service.py  │
└──────┬─────────────────────────┬───────────────────────-┘
       │ 调用                    │ 调用
┌──────▼───────────┐   ┌─────────▼───────────────────────┐
│    运行时层       │   │          存储访问层              │
│   runtime/        │   │   storage/stores/               │
│  agent_runtime.py │   │   session_store.py              │
│  tool_executor.py │   └─────────┬───────────────────────┘
│  message_builder  │             │ 操作
│  response_handler │   ┌─────────▼───────────────────────┐
└──────┬────────────┘   │          ORM 模型层             │
       │ 调用            │     storage/models.py            │
┌──────▼────────────┐   │   SessionRecord                 │
│    模型适配层      │   │   SessionRunRecord (run_status) │
│    model/          │   │   ToolCallRecord                │
│  openai_adapter.py │   └─────────┬───────────────────────┘
│  → httpx 异步流    │             │ 操作
└───────────────────┘   ┌─────────▼───────────────────────┐
                        │          数据库层                │
                        │   SQLite + SQLAlchemy           │
                        │   agent_session.db              │
                        └─────────────────────────────────┘

────────────── 横切关注点 ──────────────
core/schemas.py        → 所有层共用的 Pydantic 模型
core/agent_definition  → Agent 定义结构
skills/                → Skill 加载与配置
context/               → Prompt 构建与压缩
trace/                 → 事件追踪
```

---

## 功能链路详解

### 1. 普通对话 `POST /run`

```
前端
  └─ api.runPass(session_id, user_input)
        ↓ HTTP POST /run
路由层  run_routes.py
  └─ run_agent_service(agent_input, db)
        ↓
服务层  run_service.py
  ├─ _prepare_run_context()    ← 读 session 历史、agent 定义
  ├─ Agent.run()               ← 调运行时
  │     ↓
  │   运行时  agent_runtime.py
  │     ├─ model_adapter.generate()   ← 同步调大模型
  │     └─ handle_tool_calls()        ← 有工具则执行
  └─ _persist_run_result()     ← 写 session state 到 DB
        ↓
存储层  session_store.py → SQLite
        ↓ HTTP 200 JSON
前端  显示 reply
```

---

### 2. 流式对话 `POST /run/stream`

```
前端
  └─ api.streamRun(session_id, input, signal)
        ↓ HTTP POST /run/stream（长连接 SSE）
路由层  run_routes.py
  └─ StreamingResponse(async_stream_agent_service())
        ↓
服务层  run_service.py  async_stream_agent_service()
  ├─ yield SSE: {type:"start", run_id}
  ├─ _prepare_run_context()
  ├─ async for item in Agent.async_stream_run():
  │     ↓
  │   运行时  agent_runtime.py
  │     ├─ async for token in openai_adapter.async_stream_generate()
  │     │     ↓
  │     │   模型层  openai_adapter.py
  │     │     └─ httpx.stream POST → OpenAI API（长连接）
  │     │           ↓ 逐 token 返回
  │     ├─ yield str(token)          → 服务层 yield SSE: {type:"delta"}
  │     └─ async_handle_tool_calls() → 服务层 yield SSE: {type:"agent_event"}
  ├─ _persist_run_result()    ← 写 DB，run_status=completed
  └─ yield SSE: {type:"end"}
        ↓ 逐帧推送到前端
前端
  ├─ start       → 记录 run_id
  ├─ delta       → 追加到 streamingTimeline，打字机效果
  ├─ agent_event → 追加工具事件到 streamingTimeline
  └─ end         → 冻结消息，刷新 sessions 列表
```

---

### 3. Stop 按钮

```
用户点 Stop 按钮（MessageComposer.vue 右下角）
  ↓
useWorkspace.stopStreaming()
  ├─ 1. 抓 partialReply（streamingTimeline 里的 text 片段拼接）
  ├─ 2. abortController.abort()
  │         ↓
  │       fetch 抛出 AbortError
  │       sendMessage() catch → 静默处理（不报错）
  │       finally → isStreaming=false，清空 streamingTimeline
  │
  ├─ 3. POST /sessions/{id}/runs/{run_id}/finalize
  │         ↓
  │       run_routes.py → finalize_run_service()
  │         ├─ session_store.save_partial_run()   ← 写截断内容为 reply
  │         └─ session_store.update_run_status()  ← run_status=cancelled
  │
  └─ 4. currentMessages 追加 {content: partialReply, stopped: true}
              ↓
            MessageList.vue 渲染 ⏹ Stopped 标记

注：后端大模型请求无法取消，但工具结果不会被消费，
    第 2 次大模型请求不会发出。
```

---

### 4. 工具调用（含可观测性）

```
Agent 收到大模型返回的 tool_call 指令
  ↓
运行时  tool_executor.py  async_handle_tool_calls()
  │
  ├─ on_tool_start(tool_name, tool_call_id, input_json)
  │     ↓ callback（由服务层注入）
  │   run_service.py → store.create_tool_call()
  │     └─ DB: tool_call_records INSERT (status=running)
  │
  ├─ asyncio.wait_for(
  │     asyncio.to_thread(tool_registry.execute, ...),
  │     timeout=30 秒
  │   )
  │     ├─ 执行成功 → finish_status = "completed"
  │     ├─ 执行失败 → finish_status = "failed"
  │     └─ 超时     → finish_status = "timeout"
  │
  └─ on_tool_finish(record_id, status, result_json)
        ↓ callback
      run_service.py → store.finish_tool_call()
        └─ DB: tool_call_records UPDATE (status, result_json, finished_at)
```

---

### 5. Run 详情查询 `GET /sessions/{id}/runs/{run_id}`

```
调用方（前端 / curl）
  └─ GET /sessions/{session_id}/runs/{run_id}
        ↓
路由层  run_routes.py
  └─ get_run_detail_service(session_id, run_id, db)
        ↓
服务层  run_service.py
  └─ store.get_run_detail(run_id)
        ↓
存储层  session_store.py
  ├─ 查 session_runs WHERE run_id=?
  └─ 查 tool_call_records WHERE run_id=? ORDER BY id ASC
        ↓
路由层  拼装 RunDetailResponse
        ↓ HTTP 200 JSON
{
  "run_id": "...",
  "run_status": "completed | cancelled | running | failed",
  "user_input": "...",
  "reply": "...",
  "tool_calls": [
    {
      "tool_name": "web_search",
      "status": "completed | failed | timeout",
      "input_json": "...",
      "result_json": "...",
      "started_at": "...",
      "finished_at": "..."
    }
  ]
}
```

---

### 6. Session 管理

```
创建    POST /sessions             → create_session()      → DB INSERT sessions
查列表   GET  /sessions             → get_sessions()        → DB SELECT all
查详情   GET  /sessions/{id}        → get_session_detail()  → DB SELECT + state
重命名   PATCH /sessions/{id}       → rename_session()      → DB UPDATE name
删除    DELETE /sessions/{id}      → delete_session()      → DB DELETE cascade
重置    POST /reset                → reset_session()       → 清空 state.messages
压缩    POST /compact              → compact_session()     → 摘要折叠历史消息
```

---

### 7. Skill 管理

```
查列表   GET /skills                     → skill_loader.list_skills()
                                            └─ 扫描 skills/ 目录，读 SKILL.md

启用    POST /skills/{name}/enable       → skill_config.set_enabled(True)
禁用    POST /skills/{name}/disable      → skill_config.set_enabled(False)

运行时加载（每次 run 时）：
  _prepare_run_context()
    └─ skill_loader.load_skill(skill_name)
          ├─ 读 SKILL.md       → 注入 system prompt
          └─ 读 tools 定义     → 扩展可用工具列表
```

---

## SSE 帧格式

```
流式接口返回的每帧格式：
data: {"type": "<帧类型>", "data": {...}}

帧类型：
  start       → {"session_id", "run_id", "agent_name", "skill_name"}
  delta       → {"content": "单个 token 文字"}
  agent_event → {"index", "type", "tool_name", "tool_call_id", "content"}
  end         → {"reply", "state", "run_status"}
  error       → {"message"}

agent_event.type 枚举：
  assistant_tool_call  → 大模型决定调用某个工具
  tool_result          → 工具执行成功，返回结果
  tool_error           → 工具执行失败
  final_answer         → 大模型输出最终答案（跳过，已在 delta 里）
```

---

## 数据库表结构

```
sessions
  session_id    TEXT PK
  session_name  TEXT
  state_json    TEXT    ← {messages: [...]}
  created_at    DATETIME
  updated_at    DATETIME

session_runs
  run_id        TEXT PK
  session_id    TEXT FK → sessions
  run_status    TEXT    ← running / completed / cancelled / failed
  user_input    TEXT
  reply         TEXT
  agent_name    TEXT
  skill_name    TEXT
  events_json   TEXT
  created_at    DATETIME
  finished_at   DATETIME

tool_call_records
  id            INTEGER PK autoincrement
  run_id        TEXT FK → session_runs (CASCADE DELETE)
  tool_name     TEXT
  tool_call_id  TEXT
  status        TEXT    ← running / completed / failed / timeout / cancelled
  input_json    TEXT
  result_json   TEXT
  started_at    DATETIME
  finished_at   DATETIME
```
