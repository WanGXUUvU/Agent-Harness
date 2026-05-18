<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import TraceInline from './TraceInline.vue';
import type { ChildAgentInfo, StreamingItem } from '../types';
import type { useWorkspace } from '../composables/useWorkspace';
import { formatContent } from '../utils/formatContent';

interface Props {
  childAgents: ChildAgentInfo[];
  activeIndex: number | null;
  workspace: ReturnType<typeof useWorkspace>;
}

interface Emits {
  (e: 'update:activeIndex', idx: number): void;
  (e: 'close', idx: number): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const childTimelines = ref<Record<string, StreamingItem[]>>({});
const childMeta = ref<Record<string, { user_input: string; reply: string }>>({});
const isLoadingTimeline = ref(false);

// 从 API 加载子 Agent 的 timeline
const loadChildTimeline = async (runId: string) => {
  try {
    isLoadingTimeline.value = true;
    const sessionId = props.workspace.activeSessionId.value;
    if (!sessionId) return;
    
    // 调用 API 获取 trace（按 run_id）
    const trace = await props.workspace.api.getTrace(sessionId, runId);
    
    if (trace.runs && trace.runs.length > 0) {
      const run = trace.runs[0];
      // 将 events 转换为 StreamingItem 格式
      const timeline: StreamingItem[] = run.events.map(evt => ({
        kind: 'event' as const,
        event: evt,
      }));
      childTimelines.value[runId] = timeline;
      childMeta.value[runId] = { user_input: run.user_input ?? '', reply: run.reply ?? '' };
    }
  } catch (err: unknown) {
    // 子 Agent 还在运行时 API 返回 404，属于正常情况，不打印 error
    const msg = err instanceof Error ? err.message : String(err);
    if (!msg.includes('trace_not_found') && !msg.includes('Trace not found')) {
      console.error('Failed to load child timeline:', err);
    }
  } finally {
    isLoadingTimeline.value = false;
  }
};

// 获取当前活跃的子 Agent
const activeChildAgent = computed(() => {
  if (props.activeIndex === null || !props.childAgents[props.activeIndex]) {
    return null;
  }
  return props.childAgents[props.activeIndex];
});

// 获取当前活跃子 Agent 的 timeline
const activeTimeline = computed(() => {
  if (!activeChildAgent.value) return [];
  return childTimelines.value[activeChildAgent.value.run_id] || [];
});

// 当 active index 变化时，加载新的 timeline
watch(
  () => props.activeIndex,
  async (newIdx) => {
    const sessionId = props.workspace.activeSessionId.value;
    if (newIdx === null || !props.childAgents[newIdx] || !sessionId) return;
    
    const child = props.childAgents[newIdx];
    // 如果已经加载过，不再加载
    if (childTimelines.value[child.run_id]) return;
    
    await loadChildTimeline(child.run_id);
  },
  { immediate: true }
);

// 直接监听 workspace.childAgentsBySession，确保轮询更新一定能触发
// （openChildAgents 是 App.vue 的独立 ref，依赖追踪可能不可靠）
watch(
  () => {
    const sessionId = props.workspace.activeSessionId.value;
    const child = activeChildAgent.value;
    if (!sessionId || !child) return null;
    const children = props.workspace.childAgentsBySession.value[sessionId] ?? [];
    return children.find(c => c.run_id === child.run_id)?.status ?? null;
  },
  async (newStatus) => {
    if (newStatus !== 'done' && newStatus !== 'error') return;
    const child = activeChildAgent.value;
    if (!child) return;
    if (!childTimelines.value[child.run_id] || childTimelines.value[child.run_id].length === 0) {
      await loadChildTimeline(child.run_id);
    }
  },
  { immediate: true }
);

// 获取 child agent 的显示颜色（与 sidebar 保持一致）
const CHILD_COLORS = ['#7c8ff7', '#f7a07c', '#7cf7b4', '#f7e07c', '#d07cf7', '#7cd4f7'];
const getChildColor = (idx: number) => CHILD_COLORS[idx % CHILD_COLORS.length];

// 获取子 Agent 在 childAgents 数组中的原始 index
const getChildIndex = (child: ChildAgentInfo) => {
  return props.childAgents.indexOf(child);
};
</script>

<template>
  <div class="child-agent-panel">
    <!-- 标签页头 -->
    <div class="child-tabs-header">
      <div class="child-tabs">
        <div
          v-for="(child, idx) in childAgents"
          :key="child.run_id"
          class="child-tab"
          :class="{ active: activeIndex === idx }"
          @click="$emit('update:activeIndex', idx)"
        >
          <span class="tab-dot" :style="{ background: getChildColor(idx) }"></span>
          <span class="tab-name">{{ child.agent_name }}</span>
          <span v-if="child.status === 'running'" class="tab-spinner"></span>
          <span v-else-if="child.status === 'done'" class="tab-status">✓</span>
          <span v-else-if="child.status === 'error'" class="tab-status error">✗</span>
          <button 
            class="tab-close" 
            @click.stop="$emit('close', idx)"
            title="Close"
          >
            ✕
          </button>
        </div>
      </div>
    </div>

    <!-- 内容区 -->
    <div class="child-content">
      <div v-if="isLoadingTimeline" class="loading-state">
        <div class="spinner"></div>
        <span>加载对话记录…</span>
      </div>
      <div v-else-if="!activeChildAgent" class="empty-state">
        <span>选择一个子 Agent 查看</span>
      </div>
      <div v-else class="timeline-view">
        <!-- 子 Agent 信息头 -->
        <div class="child-info-header">
          <div class="child-info-title">
            <span class="child-dot" :style="{ background: getChildColor(getChildIndex(activeChildAgent)) }"></span>
            <span>{{ activeChildAgent.agent_name }}</span>
          </div>
          <span class="child-info-status" :class="activeChildAgent.status">
            {{ activeChildAgent.status }}
          </span>
        </div>

        <!-- 用户输入 -->
        <div v-if="activeChildAgent && childMeta[activeChildAgent.run_id]" class="child-io-block">
          <div class="child-io-label">任务输入</div>
          <div class="child-io-content message-text" v-html="formatContent(childMeta[activeChildAgent.run_id].user_input)"></div>
        </div>

        <!-- Timeline 展示 -->
        <div class="timeline-container">
          <div v-if="activeTimeline.length === 0" class="timeline-empty">
            暂无执行记录
          </div>
          <TraceInline
            v-else
            :events="activeTimeline.filter(item => item.kind === 'event').map(item => (item as any).event)"
            :autoExpand="true"
          />
        </div>

        <!-- 最终输出 -->
        <div v-if="activeChildAgent && childMeta[activeChildAgent.run_id]?.reply" class="child-io-block child-io-reply">
          <div class="child-io-label">最终输出</div>
          <div class="child-io-content message-text" v-html="formatContent(childMeta[activeChildAgent.run_id].reply)"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.child-agent-panel {
  display: flex;
  flex-direction: column;
  border-left: 1px solid var(--border-dim);
  background: var(--bg-panel);
  overflow: hidden;
  height: 100%;
  flex-shrink: 0;
}

/* 标签页头 */
.child-tabs-header {
  padding: 0;
  border-bottom: 1px solid var(--border-dim);
  background: var(--bg-app);
}

.child-tabs {
  display: flex;
  gap: 0;
  overflow-x: auto;
  overflow-y: hidden;
}

.child-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  border-right: 1px solid var(--border-dim);
  cursor: pointer;
  transition: var(--transition-fast);
  white-space: nowrap;
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-app);
}

.child-tab:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.child-tab.active {
  background: var(--bg-panel);
  color: var(--text-primary);
  border-bottom: 2px solid var(--accent);
  padding-bottom: 8px;
}

.tab-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.tab-name {
  flex: 0 1 auto;
}

.tab-status {
  flex-shrink: 0;
  font-weight: 600;
  color: var(--success);
}

.tab-status.error {
  color: var(--danger);
}

.tab-spinner {
  width: 8px;
  height: 8px;
  border: 2px solid rgba(96, 165, 250, 0.3);
  border-top-color: var(--accent-blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.tab-close {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0;
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 2px;
  transition: var(--transition-fast);
  flex-shrink: 0;
  font-size: 12px;
}

.tab-close:hover {
  background: var(--bg-elevated);
  color: var(--text-primary);
}

/* 内容区 */
.child-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.loading-state,
.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-muted);
  font-size: 12px;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(96, 165, 250, 0.2);
  border-top-color: var(--accent-blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.timeline-view {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow-y: auto;
}

.child-info-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-dim);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--bg-app);
  flex-shrink: 0;
}

.child-info-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
}

.child-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.child-info-status {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  background: rgba(96, 165, 250, 0.1);
  color: var(--accent-blue);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.child-info-status.done {
  background: rgba(80, 227, 194, 0.1);
  color: var(--success);
}

.child-info-status.error {
  background: rgba(255, 69, 58, 0.1);
  color: var(--danger);
}

.timeline-container {
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.timeline-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 12px;
}

.child-io-block {
  padding: 8px 12px;
  border-top: 1px solid var(--border-dim);
}

.child-io-reply {
  border-bottom: none;
  background: color-mix(in srgb, var(--accent-blue) 6%, transparent);
}

.child-io-label {
  font-size: 10px;
  font-family: var(--font-mono);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 4px;
}

.child-io-content {
  font-size: 12px;
  color: var(--text-primary);
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
