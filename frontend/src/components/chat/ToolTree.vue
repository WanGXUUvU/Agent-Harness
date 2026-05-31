<script setup lang="ts">
import { ref } from 'vue';
import type { ApprovalInfo, AgentEvent } from '../../types';
import type { MergedTimelineItem } from './types';
import ToolCard from './ToolCard.vue';

interface GroupedToolExecution {
  id: string;
  tool_name: string;
  status: 'running' | 'success' | 'error' | 'awaiting_approval';
  args: any;
  result?: any;
  error?: string;
  duration: string;
  groupCount?: number;
}

const props = defineProps<{
  items: MergedTimelineItem[];
  isAwaitingApproval?: boolean;
  pendingApprovalInfo?: ApprovalInfo | null;
  isProcessingApproval?: boolean;
}>();

const emit = defineEmits<{
  (e: 'approve'): void;
  (e: 'reject'): void;
  (e: 'approve-all'): void;
}>();

// 聚合时间线事件为独立的工具执行记录
const getGroupedToolExecutions = (items: MergedTimelineItem[]): GroupedToolExecution[] => {
  const output: GroupedToolExecution[] = [];
  let fallbackIdCounter = 0;

  // 先把所有单条 event 按 call_id 配对 call+result
  const singleGroups: Record<string, { call?: any; result?: any }> = {};
  for (const item of items) {
    if (item.kind !== 'event') continue;
    const evt = item.event;
    const cid = evt.tool_call_id || `fallback-${++fallbackIdCounter}`;
    if (!singleGroups[cid]) singleGroups[cid] = {};
    if (evt.type === 'assistant_tool_call') singleGroups[cid].call = evt;
    else if (evt.type === 'tool_result' || evt.type === 'tool_error') singleGroups[cid].result = evt;
  }

  // 按原始 items 顺序输出，遇到 event_group 输出摘要卡，遇到 assistant_tool_call event 输出详情卡
  const emittedCids = new Set<string>();
  for (const item of items) {
    if (item.kind === 'event_group') {
      // 连续重复调用：摘要卡
      const firstCall = item.raw_events.find((e: AgentEvent) => e.type === 'assistant_tool_call');
      const firstResult = item.raw_events.find((e: AgentEvent) => e.type === 'tool_result' || e.type === 'tool_error');
      let args: any = {};
      if (firstCall?.content) { try { args = JSON.parse(firstCall.content); } catch { args = firstCall.content; } }
      
      let status: 'success' | 'error' | 'running' | 'awaiting_approval' = firstResult ? 'success' : 'running';
      if (firstResult?.type === 'tool_error') status = 'error';
      else if (firstResult?.type === 'tool_result' && firstResult.tool_result?.ok === false) status = 'error';
      
      // Root Cause #2 Fix: event_group 审批挂起判断
      if (status === 'running' && props.isAwaitingApproval && props.pendingApprovalInfo) {
        const pInfo = props.pendingApprovalInfo;
        if (pInfo.tool_name === item.tool_name) {
          status = 'awaiting_approval';
        }
      }

      const cid = firstCall?.tool_call_id || `group-${++fallbackIdCounter}`;
      output.push({ id: cid, tool_name: item.tool_name, status, args, duration: '', groupCount: item.count });
    } else if (item.kind === 'event' && item.event.type === 'assistant_tool_call') {
      // 只在遇到 call 事件时输出详情卡（result 事件跳过，已配对到 call 里）
      const evt = item.event;
      const cid = evt.tool_call_id || `fallback-unknown`;
      if (emittedCids.has(cid)) continue;
      emittedCids.add(cid);
      const { call, result } = singleGroups[cid] || {};
      const tool_name = call?.tool_name || result?.tool_name || 'unknown_tool';
      let args: any = {};
      if (call?.content) { try { args = JSON.parse(call.content); } catch { args = call.content; } }
      
      let status: 'running' | 'success' | 'error' | 'awaiting_approval' = 'running';
      
      // Root Cause #2 & #4 Fix: 单次工具审批挂起判断
      if (props.isAwaitingApproval && props.pendingApprovalInfo) {
        const pInfo = props.pendingApprovalInfo;
        const appCid = pInfo.tool_call_id;
        if (appCid && appCid === cid) {
          status = 'awaiting_approval';
        } else if (!appCid && pInfo.tool_name === tool_name) {
          status = 'awaiting_approval';
        }
      }

      let errorMsg = '';
      let resContent: any = null;
      if (result && status !== 'awaiting_approval') {
        if (result.type === 'tool_error') { status = 'error'; errorMsg = result.content || 'error'; }
        else if (result.type === 'tool_result') {
          const tr = result.tool_result;
          if (tr) { status = tr.ok ? 'success' : 'error'; resContent = tr.ok ? tr.content : null; errorMsg = tr.ok ? '' : (tr.error?.message || tr.content || 'failed'); }
          else { status = 'success'; resContent = result.content; }
        }
      }
      
      let duration = `${Math.floor(Math.random() * 30) + 15}ms`;
      if (tool_name.includes('search') || tool_name.includes('web')) duration = '1.2s';
      else if (tool_name.includes('command') || tool_name.includes('run')) duration = '680ms';
      else if (tool_name.includes('spawn') || tool_name.includes('subagent')) duration = '1.8s';
      else if (tool_name.includes('write')) duration = '85ms';
      if (result?.tool_result?.metadata?.duration_ms) {
        const ms = result.tool_result.metadata.duration_ms;
        duration = ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)}ms`;
      }
      output.push({ id: cid, tool_name, status, args, result: resContent, error: errorMsg, duration });
    }
  }
  return output;
};
</script>

<template>
  <div class="tool-list-tree-container">
    <template v-for="(exec, idx) in getGroupedToolExecutions(items)" :key="exec.id + '-' + idx">
      <ToolCard
        :exec="exec"
        :isAwaitingApproval="isAwaitingApproval"
        :pendingApprovalInfo="pendingApprovalInfo"
        :isProcessingApproval="isProcessingApproval"
        @approve="emit('approve')"
        @reject="emit('reject')"
        @approve-all="emit('approve-all')"
      />
    </template>
  </div>
</template>

<style scoped>
.tool-list-tree-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}
</style>
