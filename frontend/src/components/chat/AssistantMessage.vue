<script setup lang="ts">
import { computed, ref } from 'vue';
import type { AgentMessage, TraceRunSummary, StreamingItem, ApprovalInfo } from '../../types';
import type { TimelineChunk, MergedTimelineItem, ThinkingSegment } from './types';
import { formatContent } from '../../utils/formatContent';
import ThinkingBlock from './ThinkingBlock.vue';
import ToolTree from './ToolTree.vue';
import ToolIcons from '../common/ToolIcons.vue';

const props = defineProps<{
  message: AgentMessage;
  msgIndex: number;
  isLast: boolean;
  traceRuns?: TraceRunSummary[];
  lastCompletedRun?: TraceRunSummary | null;
  isAwaitingApproval?: boolean;
  pendingApprovalInfo?: ApprovalInfo | null;
  isProcessingApproval?: boolean;
}>();

const emit = defineEmits<{
  (e: 'approve'): void;
  (e: 'reject'): void;
  (e: 'approve-all'): void;
}>();

const mergeThreshold = 2; // >=2次同名调用折叠
const nonCollapsibleToolNames = new Set([
  'write_file',
  'delete_file',
  'replace_in_file',
  'rename_file',
  'move_file',
  'copy_file',
]);

const collapsedChunks = ref<Record<string, boolean>>({});
const toggleChunk = (id: string) => {
  collapsedChunks.value = { ...collapsedChunks.value, [id]: !(collapsedChunks.value[id] ?? true) };
};

const buildMergedItems = (events: any[]): MergedTimelineItem[] => {
  const items: MergedTimelineItem[] = [];
  let cg: { tool_name: string; events: any[] } | null = null;
  
  const flushG = () => {
    if (!cg) return;
    const callCount = cg.events.filter(e => e.type === 'assistant_tool_call').length;
    const shouldCollapse =
      !nonCollapsibleToolNames.has(cg.tool_name) && callCount >= mergeThreshold;
    if (!shouldCollapse) {
      cg.events.forEach(e => items.push({ kind: 'event', event: e }));
    } else {
      items.push({ kind: 'event_group', tool_name: cg.tool_name, count: callCount, raw_events: cg.events });
    }
    cg = null;
  };
  
  for (const e of events) {
    if (e.type === 'final_answer') continue;
    const tName = e.tool_name || e.type;
    if (!cg) {
      cg = { tool_name: tName, events: [e] };
    } else if (cg.tool_name === tName) {
      cg.events.push(e);
    } else {
      flushG();
      cg = { tool_name: tName, events: [e] };
    }
  }
  flushG();
  return items;
};

const chunkTimeline = computed((): TimelineChunk[] => {
  const timeline = getSyntheticTimeline.value;
  if (!timeline) return [];
  
  const chunks: TimelineChunk[] = [];
  type RawSegment = { kind: 'text'; content: string } | { kind: 'tools'; events: any[] };
  let thinkingSegments: RawSegment[] = [];
  let inThinking = false;
  let currentStandaloneTools: any[] = [];
  let currentText = '';

  const flushThinking = () => {
    if (thinkingSegments.length === 0) return;
    const allText = thinkingSegments.filter(s => s.kind === 'text').map(s => s.content).join('');
    const segments: ThinkingSegment[] = thinkingSegments.map(seg => {
      if (seg.kind === 'text') return { kind: 'text', content: seg.content };
      return { kind: 'tools', items: buildMergedItems(seg.events) };
    });
    chunks.push({
      type: 'thinking',
      content: allText,
      id: `msg-${props.msgIndex}-thinking-${chunks.length}`,
      segments
    });
    thinkingSegments = [];
    inThinking = false;
  };

  const flushStandaloneTools = () => {
    if (currentStandaloneTools.length === 0) return;
    const items = buildMergedItems(currentStandaloneTools);
    if (items.length > 0) {
      chunks.push({
        type: 'tools',
        items,
        raw_count: items.reduce((acc: number, item: MergedTimelineItem) => acc + (item.kind === 'event_group' ? item.raw_events.length : 1), 0),
        id: `msg-${props.msgIndex}-tools-${chunks.length}`
      });
    }
    currentStandaloneTools = [];
  };
  
  for (const item of timeline) {
    if (item.kind === 'thinking') {
      if (inThinking) {
        flushThinking();
      }
      flushStandaloneTools();
      if (currentText.length > 0) {
        chunks.push({ type: 'text', content: currentText, id: `msg-${props.msgIndex}-text-${chunks.length}` });
        currentText = '';
      }
      inThinking = true;
      thinkingSegments.push({ kind: 'text', content: item.content });
    } else if (item.kind === 'text') {
      flushThinking();
      flushStandaloneTools();
      currentText += item.content;
    } else {
      if (currentText.length > 0) {
        chunks.push({ type: 'text', content: currentText, id: `msg-${props.msgIndex}-text-${chunks.length}` });
        currentText = '';
      }
      if (inThinking) {
        const lastSeg = thinkingSegments.at(-1);
        if (lastSeg && lastSeg.kind === 'tools') {
          lastSeg.events.push(item.event);
        } else {
          thinkingSegments.push({ kind: 'tools', events: [item.event] });
        }
      } else {
        currentStandaloneTools.push(item.event);
      }
    }
  }
  
  flushThinking();
  flushStandaloneTools();
  if (currentText.length > 0) {
    chunks.push({ type: 'text', content: currentText, id: `msg-${props.msgIndex}-text-${chunks.length}` });
  }
  
  return chunks;
});

const getSyntheticTimeline = computed((): StreamingItem[] => {
  if (props.message.timeline && props.message.timeline.length > 0) {
    return props.message.timeline;
  }
  
  const r = findRun.value;
  const items: StreamingItem[] = [];
  
  if (r && r.events) {
    r.events.forEach(e => {
      items.push({ kind: 'event', event: e });
    });
  }
  
  if (props.message.content) {
    items.push({ kind: 'text', content: props.message.content });
  }
  
  return items;
});

const findRun = computed((): TraceRunSummary | undefined => {
  if (props.isLast && props.lastCompletedRun) return props.lastCompletedRun;
  
  // 按照 parent 的上下文解析对应的 run
  // 这一步由 traceRuns 进行顺序对齐
  if (props.traceRuns && props.msgIndex >= 0 && props.traceRuns.length > props.msgIndex) {
    return props.traceRuns[props.msgIndex];
  }
  return undefined;
});

const getToolNamesList = (chunk: TimelineChunk): string => {
  if (chunk.type !== 'tools') return '';
  const names = new Set<string>();
  chunk.items.forEach((item: MergedTimelineItem) => {
    if (item.kind === 'event') {
      if (item.event.tool_name) names.add(item.event.tool_name);
    } else if (item.kind === 'event_group') {
      names.add(item.tool_name);
    }
  });
  return Array.from(names).join(', ') || '工具组件';
};

const hasError = (chunk: TimelineChunk): boolean => {
  if (chunk.type !== 'tools') return false;
  return chunk.items.some((item: MergedTimelineItem) => {
    if (item.kind === 'event') {
      return item.event.type === 'tool_error' || (item.event.type === 'tool_result' && item.event.tool_result?.ok === false);
    }
    return false;
  });
};

const isChunkCollapsed = (id: string) => collapsedChunks.value[id] ?? true;

// 💡 采用事件代理拦截来自子元素代码块中 Copy 按钮的点击事件，安全、快速且彻底免除 inline JS 漏洞
const handleCodeBlockClick = (e: MouseEvent) => {
  const target = e.target as HTMLElement;
  const btn = target.closest('.copy-code-btn') as HTMLButtonElement | null;
  if (!btn) return;

  const codeBlock = btn.closest('.code-block');
  const codeEl = codeBlock?.querySelector('pre code');
  if (!codeEl) return;

  const rawCode = codeEl.textContent || '';

  navigator.clipboard.writeText(rawCode)
    .then(() => {
      btn.classList.add('copied');
      const textSpan = btn.querySelector('.copy-text');
      if (textSpan) textSpan.textContent = 'Copied';

      setTimeout(() => {
        btn.classList.remove('copied');
        if (textSpan) textSpan.textContent = 'Copy';
      }, 2000);
    })
    .catch(err => {
      console.error('📋 复制代码块失败:', err);
    });
};
</script>

<template>
  <div class="assistant-message-content">
    <template v-for="chunk in chunkTimeline" :key="chunk.id">
      <!-- 渲染文本 Chunk -->
      <div 
        v-if="chunk.type === 'text'" 
        class="message-text" 
        v-html="formatContent(chunk.content)" 
        @click="handleCodeBlockClick"
      ></div>
      
      <!-- 渲染思考过程 -->
      <ThinkingBlock
        v-else-if="chunk.type === 'thinking'"
        :chunk="chunk"
        :isAwaitingApproval="isAwaitingApproval"
        :pendingApprovalInfo="pendingApprovalInfo"
        :isProcessingApproval="isProcessingApproval"
        @approve="emit('approve')"
        @reject="emit('reject')"
        @approve-all="emit('approve-all')"
      />
      
      <!-- 渲染独立工具链 -->
      <div 
        v-else-if="chunk.type === 'tools'" 
        class="history-trace-container" 
        :class="{ 'has-error': hasError(chunk) }"
      >
        <button class="timeline-toggle" @click="toggleChunk(chunk.id)">
          <div class="toggle-left-indicator" :class="hasError(chunk) ? 'status-error' : 'status-success'"></div>
          <span class="evt-icon-box header-icon-box" :class="hasError(chunk) ? 'status-error' : 'status-success'">
            <ToolIcons :type="hasError(chunk) ? 'tool_error' : 'assistant_tool_call'" :size="11" />
          </span>
          <span class="toggle-verb">
            <template v-if="hasError(chunk)">调用失败: {{ getToolNamesList(chunk) }}</template>
            <template v-else>链式调用: {{ getToolNamesList(chunk) }}</template>
          </span>
          <span class="toggle-count">共 {{ chunk.raw_count }} 步</span>
          <svg class="toggle-chevron" :class="{ open: !isChunkCollapsed(chunk.id) }" viewBox="0 0 24 24" width="11" height="11" stroke="currentColor" stroke-width="2.5" fill="none">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </button>

        <div class="tool-tree" :class="{ collapsed: isChunkCollapsed(chunk.id) }">
          <ToolTree
            :items="chunk.items"
            :isAwaitingApproval="isAwaitingApproval"
            :pendingApprovalInfo="pendingApprovalInfo"
            :isProcessingApproval="isProcessingApproval"
            @approve="emit('approve')"
            @reject="emit('reject')"
            @approve-all="emit('approve-all')"
          />
        </div>
      </div>
    </template>
    
    <div v-if="message.stopped" class="stopped-label">⏹ Stopped</div>
  </div>
</template>

<style scoped>
.assistant-message-content {
  width: 100%;
  display: flex;
  flex-direction: column;
}
</style>
