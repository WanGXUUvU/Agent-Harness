# TASK-084: 前端消息树模块化重构与顶奢工具审批视觉收口

## 1. 核心任务定义 (Task Refactoring)
**目标**：将臃肿的 `MessageList.vue` 进行模块化拆分，彻底消除 1300+ 行的单文件负担；同时在拆分后的组件树中，对工具审批（Approve / Reject / Approve All）进行高内聚、高颜值的交互设计，实现符合赛博朋克极客风的 Premium UI 效果，并 100% 连通审批流。

---

## 2. 新任务拆解模板 (AGENTS.md Template)

### 用户动作：
1. 用户输入一条同时触发多个工具的请求（例如：需要修改多个文件，触发多个 `write_file` 审批事件）。
2. 用户在消息流中直接点击待审批工具卡片中的 **【批准】 (Approve)**、**【拒绝】 (Reject)** 或 **【全部批准】 (Approve All)** 按钮。

### 用户会看到：
1. **多审批卡片并存与排队**：卡片以优雅的 HSL 渐变呼吸微光边框形式嵌入在对话流中，完美配合暗黑主题。
2. **即时交互微动效**：悬浮按钮有平滑的 Scale 缩放与 Glow 聚焦发光，点击后按钮处于 Loading/Processing 状态。
3. **状态平滑过渡**：审批完成后，原卡片状态和按钮转换，以淡入淡出动效转为执行结果或拒绝标签，不发生闪烁。

### 新数据从哪里产生 / 存在哪里：
1. 审批事件和挂起状态数据：流式 `streamingTimeline`（SSE `approval_required`）与 `traceRuns` 中，在 `useWorkspace` 内存态中维持响应式。
2. 审批操作后的结果：前端发起请求后由后端返回，并在会话 Timeline 中增加新的 `tool_result`。

### 前端调哪个接口 / need 改的层：
1. 前端调用 `/run/session/{sessionId}/approve` 和 `/run/session/{sessionId}/reject`。
2. 改造层：`frontend/src/components/chat/`
   - `MessageList.vue` -> 容器层，接收 Props 与派发消息。
   - `AssistantMessage.vue` -> AI 气泡及 Timeline 编排层。
   - `ThinkingBlock.vue` -> AI 思考过程及折叠面板。
   - `ToolTree.vue` & `ToolCard.vue` -> 工具链式执行、参数详情与**审批交互区（ApprovalSection）**。

---

## 3. 范围内与范围外 (In & Out of Scope)

### 范围内：
1. **彻底拆分**：将 `MessageList.vue` 的核心大块进行拆解，在 `components/chat/` 新增 `AssistantMessage.vue`, `ThinkingBlock.vue`, `ToolTree.vue`, `ToolCard.vue`。
2. **完美支持 reactivity**：确保拆分出的组件中的 props 传递均采用正确的响应式方式，杜绝在模板内读取 `.value` 的失活现象。
3. **顶奢审批 UI 设计**：
   - 使用 HSL 渐变、磨砂玻璃态、立体悬浮阴影构建审批界面。
   - 三按钮设计：【批准】 (Approve) 绿色呼吸态，【全部批准】 (Approve All) 渐变微光态，【拒绝】 (Reject) 红色警示态。
4. **Tool Batch 状态机闭环**：配合 event_group 路径，完美解决并发工具（如 multiple write_file）在审批时显示空/显示 running 的 Bug。

### 范围外：
1. 后端 API 路由及状态机的重新编写。
2. 全局设置/其他菜单的视觉大改。

---

## 4. 实现步骤 (Implementation Plan)

### Step 1: 基础骨架与响应式重构
- 确保 `CodingView.vue` 和 `AssistantView.vue` 中传递给 `ChatPanel` 乃至子组件的属性，皆在 setup 顶层封装为计算属性（如 `const wIsAwaitingApproval = computed(...)`），完全解决响应式丢失。

### Step 2: 组件拆分与定义
- **`ToolCard.vue` [NEW]**：专门负责单个/聚合工具的状态与参数渲染，并以极其精美的 UI 绘制【审批操作区】。
- **`ToolTree.vue` [NEW]**：包装一组 MergedTimelineItem，做折叠和层级组织。
- **`ThinkingBlock.vue` [NEW]**：负责渲染 `<div class="thinking-container">`，包含内部文本和嵌入的工具树。
- **`AssistantMessage.vue` [NEW]**：承载消息的角色头部、时间线的分块处理与渲染。
- **`MessageList.vue` [MODIFY]**：做大幅清洗瘦身，降为 100 行左右的干净主容器，只做消息映射循环。

### Step 3: Tool Batch 与 event_group 审批收口
- 修复 `getGroupedToolExecutions` 逻辑，在 items 聚合时判断 `isAwaitingApproval && pendingApprovalInfo`，使 `event_group` 能够准确捕获待审批状态并映射到对应的 `ToolCard` 或全局审批卡片。

### Step 4: 编译打包验证
- 严格执行 `npm run build`，确保所有组件在 TS 严苛模式下 100% 通过编译，且无任何 runtime 警告。

---

## 5. 完成标准 (Criteria of Success)
1. `npm run build` 成功通过，无编译/类型错误。
2. 前端能够自动、流畅地弹出挂起的工具审批卡片，界面拥有磨砂渐变和微动效。
3. 用户在页面直接点击【批准】/【全部批准】/【拒绝】时，能够正确发送后端 API 恢复流，结果自然回填。
