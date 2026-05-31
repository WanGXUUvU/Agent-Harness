<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import type { ApprovalInfo } from '../../types';
import type { TimelineChunk, MergedTimelineItem, ThinkingSegment } from './types';
import ToolTree from './ToolTree.vue';

const props = defineProps<{
  chunk: TimelineChunk;
  isAwaitingApproval?: boolean;
  pendingApprovalInfo?: ApprovalInfo | null;
  isProcessingApproval?: boolean;
}>();

const emit = defineEmits<{
  (e: 'approve'): void;
  (e: 'reject'): void;
  (e: 'approve-all'): void;
}>();

// 统计 thinking chunk 内所有 tool 段的执行次数（用于 header 显示）
const countThinkingTools = computed((): number => {
  if (props.chunk.type !== 'thinking' || !props.chunk.segments) return 0;
  return props.chunk.segments
    .filter((s: ThinkingSegment) => s.kind === 'tools')
    .flatMap((s: ThinkingSegment) => (s as { kind: 'tools'; items: MergedTimelineItem[] }).items)
    .reduce((acc: number, item: MergedTimelineItem) =>
      acc + (item.kind === 'event_group' ? item.count : item.event.type === 'assistant_tool_call' ? 1 : 0), 0);
});

// 判断本思考块内是否包含当前等待审批的工具
const hasPendingApprovalInChunk = computed(() => {
  if (!props.isAwaitingApproval || !props.pendingApprovalInfo) return false;
  if (props.chunk.type !== 'thinking' || !props.chunk.segments) return false;
  
  return props.chunk.segments.some((seg: ThinkingSegment) => {
    if (seg.kind !== 'tools') return false;
    return seg.items.some((item: MergedTimelineItem) => {
      const pInfo = props.pendingApprovalInfo!;
      if (item.kind === 'event') {
        const cid = item.event.tool_call_id;
        if (cid && cid === pInfo.tool_call_id) return true;
        if (!cid && item.event.tool_name === pInfo.tool_name) return true;
      } else if (item.kind === 'event_group') {
        return item.tool_name === pInfo.tool_name;
      }
      return false;
    });
  });
});

const isCollapsed = ref(true);

// 核心优化：若包含待审批项，自动展开，方便用户操作
watch(hasPendingApprovalInChunk, (val) => {
  if (val) {
    isCollapsed.value = false;
  }
}, { immediate: true });

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value;
};
</script>

<template>
  <div v-if="chunk.type === 'thinking'" class="thinking-container">
    <button class="timeline-toggle" @click="toggleCollapse">
      <span class="toggle-verb thinking-verb">思考过程</span>
      <span v-if="countThinkingTools > 0" class="toggle-count">含 {{ countThinkingTools }} 次工具调用</span>
      
      <!-- 如果包含挂起审批，增加醒目的橙色指示器 -->
      <span v-if="hasPendingApprovalInChunk" class="pending-warning-pill font-mono">
        <span class="pulse-dot-amber"></span>
        WAITING APPROVAL
      </span>

      <svg class="toggle-chevron" :class="{ open: !isCollapsed }" viewBox="0 0 24 24" width="11" height="11" stroke="currentColor" stroke-width="2.5" fill="none">
        <polyline points="6 9 12 15 18 9"/>
      </svg>
    </button>
    
    <div class="tool-tree" :class="{ collapsed: isCollapsed }">
      <!-- 按 segments 顺序交替渲染思考文字和工具调用 -->
      <template v-if="chunk.segments && chunk.segments.length > 0">
        <template v-for="(seg, si) in chunk.segments" :key="si">
          <div v-if="seg.kind === 'text'" class="thinking-text">{{ seg.content }}</div>
          <div v-else-if="seg.kind === 'tools'" class="thinking-embedded-tools">
            <ToolTree
              :items="seg.items"
              :isAwaitingApproval="isAwaitingApproval"
              :pendingApprovalInfo="pendingApprovalInfo"
              :isProcessingApproval="isProcessingApproval"
              @approve="emit('approve')"
              @reject="emit('reject')"
              @approve-all="emit('approve-all')"
            />
          </div>
        </template>
      </template>
      <div v-else class="thinking-text">{{ chunk.content }}</div>
    </div>
  </div>
</template>

<style scoped>
.pending-warning-pill {
  font-size: 9px;
  font-weight: 700;
  color: var(--warning-amber, #FBBF24);
  background: rgba(251, 191, 36, 0.12);
  padding: 1px 6px;
  border-radius: 4px;
  margin-left: 8px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.pulse-dot-amber {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--warning-amber, #FBBF24);
  box-shadow: 0 0 6px var(--warning-amber, #FBBF24);
  animation: dotPulse 1.6s infinite ease-in-out;
}

@keyframes dotPulse {
  0%, 100% {
    transform: scale(0.9);
    opacity: 0.6;
  }
  50% {
    transform: scale(1.15);
    opacity: 1;
  }
}
</style>
