<script setup lang="ts">
import { ref, computed } from 'vue';
import type { AgentEvent } from '../types';
import ToolIcons from './common/ToolIcons.vue';

const props = defineProps<{
  events: AgentEvent[];
}>();

const expanded = ref(false);

export type MergedTimelineItem = 
  | { kind: 'event'; event: AgentEvent }
  | { kind: 'event_group'; tool_name: string; count: number; raw_events: AgentEvent[] };

const mergeThreshold = 2; // >=2次完整调用（>=4个事件）开始折叠

const groupEvents = computed(() => {
  const result: MergedTimelineItem[] = [];
  let currentGroup: { tool_name: string, events: AgentEvent[] } | null = null;
  
  const flushGroup = () => {
    if (!currentGroup) return;
    const callCount = currentGroup.events.filter(e => e.type === 'assistant_tool_call').length;
    if (callCount < mergeThreshold) {
      currentGroup.events.forEach(e => result.push({ kind: 'event', event: e }));
    } else {
      result.push({
        kind: 'event_group',
        tool_name: currentGroup.tool_name,
        count: callCount,
        raw_events: currentGroup.events
      });
    }
    currentGroup = null;
  };

  const pureEvents = props.events.filter(e => e.type !== 'final_answer'); // Filter out fake final answer events

  for (const event of pureEvents) {
    const tName = event.tool_name || event.type;
    if (!currentGroup) {
      currentGroup = { tool_name: tName, events: [event] };
    } else {
      if (currentGroup.tool_name === tName) {
        currentGroup.events.push(event);
      } else {
        flushGroup();
        currentGroup = { tool_name: tName, events: [event] };
      }
    }
  }
  flushGroup();
  return result;
});
</script>

<template>
  <div v-if="groupEvents.length > 0" class="history-trace-container">
    <button class="timeline-toggle" @click="expanded = !expanded">
      <span class="timeline-toggle-arrow" :class="{ open: expanded }">›</span>
      <span class="mono-label">工具调用 (History)</span>
      <span class="mono-label" style="color:var(--text-muted)">{{ events.filter(e => e.type !== 'final_answer').length }} 步</span>
    </button>

    <template v-for="(item, ti) in groupEvents" :key="ti">
      <div v-if="item.kind === 'event'" class="stream-event-row stagger-anim" :class="[`evt-${item.event.type}`, { 'evt-hidden': !expanded }]" :style="{ animationDelay: `${ti * 0.03}s` }">
        <span class="evt-icon"><ToolIcons :type="item.event.type"/></span>
        <span class="evt-label mono-label">{{ item.event.tool_name ?? item.event.type }}</span>
        <span v-if="item.event.content" class="evt-content">{{ item.event.content.replace(/\n/g,' ').slice(0, 80) }}{{ item.event.content.length > 80 ? '…' : '' }}</span>
      </div>
      
      <div v-else-if="item.kind === 'event_group'" class="stream-event-row evt-group stagger-anim" :class="[{ 'evt-hidden': !expanded }]" :style="{ animationDelay: `${ti * 0.03}s` }">
        <span class="evt-icon"><ToolIcons type="assistant_tool_call"/></span>
        <span class="evt-label mono-label">{{ item.tool_name }}</span>
        <span class="evt-content" style="font-weight: 500; font-style: italic;">连续执行了 {{ item.count }} 次 (Grouped {{ item.raw_events.length }} events)</span>
      </div>
    </template>
  </div>
</template>

<style scoped>
.history-trace-container {
  margin-top: 12px;
}

.timeline-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--text-primary);
  opacity: 0.8;
  padding: 4px 6px;
  border-radius: 4px;
  transition: all 0.2s ease;
  margin-bottom: 6px;
}

.timeline-toggle:hover {
  background: var(--bg-hover);
  opacity: 1;
}

.timeline-toggle-arrow {
  font-size: 16px;
  line-height: 1;
  display: inline-block;
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  transform: rotate(0deg);
  font-family: var(--font-mono);
}
.timeline-toggle-arrow.open {
  transform: rotate(90deg);
}

.stream-event-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 4px 0;
  font-size: 12px;
  border-left: 2px solid var(--border-strong);
  padding-left: 8px;
  margin: 3px 0;
  opacity: 0.85;
  overflow: hidden;
  max-height: 40px;
  transition: max-height 0.2s ease, opacity 0.2s ease, margin 0.2s ease, padding 0.2s ease;
}

.stream-event-row.evt-group {
  border-left: 2px solid var(--accent);
  background: var(--bg-active);
  border-radius: 4px;
  padding: 6px 10px;
  margin-left: -2px;
}

.stream-event-row.evt-hidden {
  max-height: 0;
  opacity: 0;
  margin: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.evt-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 2px;
}

.evt-label {
  flex-shrink: 0;
  color: var(--text-primary);
  font-weight: 500;
}

.evt-content {
  color: var(--text-muted);
  font-family: var(--font-mono);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
