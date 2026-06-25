<script setup lang="ts">
import { computed, ref } from 'vue';
import type { ApprovalInfo } from '../../types';

interface GroupedToolExecution {
  id: string;
  tool_name: string;
  status: 'running' | 'success' | 'error' | 'awaiting_approval';
  args: any;
  result?: any;
  error?: string;
  duration: string;
  groupCount?: number;
  approvalInfo?: ApprovalInfo | null;
  vfsState?: string;
}

const props = defineProps<{
  exec: GroupedToolExecution;
  isAwaitingApproval?: boolean;
  pendingApprovalInfo?: ApprovalInfo | null;
  pendingApprovalInfos?: ApprovalInfo[];
  isProcessingApproval?: boolean;
}>();

const emit = defineEmits<{
  (e: 'approve', approvalId?: string): void;
  (e: 'reject', approvalId?: string): void;
  (e: 'approve-all'): void;
}>();

const isExpanded = ref(false);

const toggleExpand = () => {
  isExpanded.value = !isExpanded.value;
};

// Check if this specific tool card is currently waiting for approval
const isThisWaitingApproval = computed(() => {
  return props.exec.status === 'awaiting_approval' && !!props.exec.approvalInfo;
});

const maxCollapsedLines = 9;
const readResultToolNames = new Set(['read_file', 'view_file', 'list_dir']);

const tryExtractFromPartialJson = (jsonStr: string, keys: string[]): string | null => {
  const clean = jsonStr.trim();
  if (!clean.startsWith('{')) return null;

  for (const key of keys) {
    // 1. Try matching fully quoted string values: "key" : "value"
    const completeRegex = new RegExp(`"${key}"\\s*:\\s*"([^"\\\\]*(?:\\\\.[^"\\\\]*)*)"`);
    const completeMatch = clean.match(completeRegex);
    if (completeMatch && completeMatch[1] !== undefined) {
      try {
        return JSON.parse(`"${completeMatch[1]}"`);
      } catch {
        return completeMatch[1];
      }
    }

    // 2. Try matching incomplete string values (streaming): "key" : "value...
    const incompleteRegex = new RegExp(`"${key}"\\s*:\\s*"([^"\\\\]*(?:\\\\.[^"\\\\]*)*)$`);
    const incompleteMatch = clean.match(incompleteRegex);
    if (incompleteMatch && incompleteMatch[1] !== undefined) {
      try {
        return JSON.parse(`"${incompleteMatch[1]}"`);
      } catch {
        return incompleteMatch[1].replace(/\\"/g, '"').replace(/\\n/g, '\n');
      }
    }

    // 3. Try matching boolean or number values: "key" : true / 123
    const primitiveRegex = new RegExp(`"${key}"\\s*:\\s*(true|false|null|\\d+)`);
    const primitiveMatch = clean.match(primitiveRegex);
    if (primitiveMatch && primitiveMatch[1] !== undefined) {
      return primitiveMatch[1];
    }
  }
  return null;
};

const fileArgsInfo = computed(() => {
  const args = props.exec.args;

  let pathVal = '';
  let contentVal: unknown = '';
  let hasContentField = false;

  const preferredPathKeys = ['TargetFile', 'path'];
  const preferredContentKeys = ['CodeContent', 'content', 'ReplacementContent', 'replacementContent'];

  if (args && typeof args === 'object') {
    const pathKey = preferredPathKeys.find(k => k in args);
    pathVal = pathKey ? args[pathKey] : '';

    const contentKey = preferredContentKeys.find(k => k in args);
    hasContentField = Boolean(contentKey);
    contentVal = contentKey ? args[contentKey] : '';
  } else if (typeof args === 'string') {
    pathVal = tryExtractFromPartialJson(args, preferredPathKeys) || '';
    hasContentField = preferredContentKeys.some(key => new RegExp(`"${key}"\\s*:`).test(args));
    contentVal = hasContentField ? tryExtractFromPartialJson(args, preferredContentKeys) ?? '' : '';
  }

  // Do not read and preview the content of read tools (like read_file, view_file, list_dir) to keep the chat clean

  if (!hasContentField) return null;

  // Extract basename for tab title
  let filename = 'file';
  if (typeof pathVal === 'string' && pathVal) {
    const parts = pathVal.split(/[/\\]/);
    filename = parts[parts.length - 1] || 'file';
  }

  const isMd = filename.toLowerCase().endsWith('.md');
  const contentStr =
    typeof contentVal === 'string'
      ? contentVal
      : contentVal === null || contentVal === undefined
        ? ''
        : JSON.stringify(contentVal, null, 2);

  // Split lines
  const lines = contentStr.split('\n');
  const totalLines = lines.length;

  return {
    path: pathVal,
    filename,
    content: contentStr,
    lines,
    totalLines,
    isMarkdown: isMd,
  };
});

const displayedLines = computed(() => {
  if (!fileArgsInfo.value) return [];
  const lines = fileArgsInfo.value.lines;
  if (isExpanded.value || isThisWaitingApproval.value) {
    return lines;
  }
  return lines.slice(0, Math.min(lines.length, maxCollapsedLines));
});

const displayedContent = computed(() => displayedLines.value.join('\n'));

const toolCnNameMap: Record<string, string> = {
  read_file: 'READ',
  write_file: 'WRITE',
  replace_file_content: 'WRITE',
  multi_replace_file_content: 'WRITE',
  view_file: 'READ',
  list_dir: 'READ',
  grep_search: 'SEARCH',
  web_search: 'SEARCH',
  run_command: 'RUN',
  invoke_subagent: 'SUBAGENT',
  define_subagent: 'SUBAGENT',
};

const compact = (value: string, max = 92): string => {
  const normalized = value.replace(/\s+/g, ' ').trim();
  return normalized.length > max ? `${normalized.slice(0, max - 1)}…` : normalized;
};

const quote = (value: string): string => `"${compact(value.replace(/"/g, '\\"'), 72)}"`;

const toolRunningNameMap: Record<string, string> = {
  read_file: 'READING',
  write_file: 'WRITING',
  replace_file_content: 'WRITING',
  multi_replace_file_content: 'WRITING',
  view_file: 'READING',
  list_dir: 'READING',
  grep_search: 'SEARCHING',
  web_search: 'SEARCHING',
  run_command: 'RUNNING',
  invoke_subagent: 'CALLING',
  define_subagent: 'DEFINING',
};

const displayToolName = computed(() => {
  if (props.exec.status === 'running') {
    const runningMapped = toolRunningNameMap[props.exec.tool_name];
    if (runningMapped) return runningMapped;
  }
  const mapped = toolCnNameMap[props.exec.tool_name];
  if (mapped) return mapped;
  return props.exec.tool_name
    .split('_')
    .filter(Boolean)
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
});

const argPreview = computed(() => {
  const args = props.exec.args;
  if (!args || (typeof args === 'object' && Object.keys(args).length === 0)) return '';

  const preferredKeys = ['TargetFile', 'query', 'q', 'command', 'cmd', 'path', 'file_path', 'url', 'pattern', 'SearchPath', 'AbsolutePath', 'DirectoryPath'];

  if (typeof args === 'string') {
    const trimmed = args.trim();
    if (trimmed.startsWith('{')) {
      const extracted = tryExtractFromPartialJson(trimmed, preferredKeys);
      if (extracted) {
        return quote(extracted);
      }
      // If we are currently running, don't fallback to printing the whole raw JSON string!
      if (props.exec.status === 'running') {
        return '';
      }
    }
    return quote(args);
  }

  // Write tools: prioritize TargetFile to show the filename
  for (const key of preferredKeys) {
    const val = args?.[key];
    if (typeof val === 'string' && val.trim()) return quote(val);
  }

  const entries = Object.entries(args).slice(0, 2).map(([key, val]) => {
    if (typeof val === 'string') return `${key}: ${quote(val)}`;
    return `${key}: ${compact(JSON.stringify(val) ?? String(val), 42)}`;
  });
  return entries.join(', ');
});

// 展示在卡片标题中的内容：只展示关键参数（文件路径/查询词/命令），动词标签已由父节点展示
const callExpression = computed(() => argPreview.value || displayToolName.value);

const summarizeValue = (value: any): string => {
  if (value === null || value === undefined || value === '') return 'Completed';
  if (typeof value === 'string') return compact(value, 116);
  if (Array.isArray(value)) return `Returned ${value.length} item${value.length === 1 ? '' : 's'}`;
  if (typeof value === 'object') {
    const candidates = ['summary', 'message', 'content', 'output', 'stdout', 'title'];
    for (const key of candidates) {
      const val = value[key];
      if (typeof val === 'string' && val.trim()) return compact(val, 116);
    }
    return compact(JSON.stringify(value), 116);
  }
  return compact(String(value), 116);
};

const resultLine = computed(() => {
  if (isThisWaitingApproval.value) return 'Waiting for approval';
  if (props.exec.status === 'running') return 'Running';
  if (props.exec.status === 'error') return summarizeValue(props.exec.error || 'Failed');

  // Override summary for read tools to not show raw file contents or JSON
  if (readResultToolNames.has(props.exec.tool_name)) {
    if (props.exec.tool_name === 'list_dir') {
      return 'List directory successfully';
    }
    let contentStr = '';
    if (typeof props.exec.result === 'string') {
      contentStr = props.exec.result;
    } else if (props.exec.result && typeof props.exec.result === 'object') {
      contentStr = props.exec.result.content || props.exec.result.output || props.exec.result.stdout || '';
    }
    if (contentStr) {
      const lines = contentStr.split('\n').length;
      return `Read ${lines} line${lines === 1 ? '' : 's'} successfully`;
    }
    return 'Read successfully';
  }

  if (props.exec.vfsState === 'staged') return `${summarizeValue(props.exec.result)} · staged`;
  return summarizeValue(props.exec.result);
});

const resultLineClass = computed(() => {
  if (props.exec.status === 'error') return 'is-error';
  if (isThisWaitingApproval.value) return 'is-warning';
  if (props.exec.status === 'running') return 'is-running';
  return 'is-success';
});

const groupSummary = computed(() => {
  const count = props.exec.groupCount ?? 0;
  const noun = count === 1 ? 'call' : 'calls';
  return `${displayToolName.value} · ${count} ${noun}`;
});

const hasDetailedContent = computed(() => {
  return (props.exec.status !== 'running' && !!fileArgsInfo.value) || !!props.exec.error || isThisWaitingApproval.value;
});
</script>

<template>
  <!-- 连续重复调用：紧凑摘要行 -->
  <div
    v-if="exec.groupCount && exec.groupCount > 1"
    class="tool-exec-card tool-exec-group-summary"
  >
    <div class="tool-exec-header">
      <span class="tool-call-expression">
        {{ groupSummary }}
      </span>
    </div>
  </div>

  <!-- 单次工具调用或待审批工具调用 -->
  <div
    v-else
    class="tool-exec-card stagger-anim"
    :class="{ 
      'is-expanded': isExpanded || isThisWaitingApproval, 
      'has-error': exec.status === 'error',
      'is-awaiting-approval': isThisWaitingApproval 
    }"
  >
    <!-- 工具头部：Claude Code 终端风格 -->
    <div class="tool-exec-header" @click="toggleExpand">
      <!-- 状态前缀符号 -->
      <span class="tool-status-prefix">
        <span v-if="exec.status === 'running'" class="prefix-running">▸</span>
        <span v-else-if="exec.status === 'success'" class="prefix-success">✓</span>
        <span v-else-if="exec.status === 'error'" class="prefix-error">×</span>
        <span v-else-if="exec.status === 'awaiting_approval'" class="prefix-approval">◆</span>
      </span>

      <div class="tool-cli-copy">
        <div class="tool-cli-main">
          <span class="tool-call-expression" :class="`status-${exec.status}`">
            {{ callExpression }}
          </span>
          <span v-if="exec.status === 'running'" class="running-indicator">
            <span class="pulse-dot"></span>
          </span>
        </div>
        <!-- 结果行：只在完成/错误/待审批时显示 -->
        <div
          v-if="exec.status !== 'running'"
          class="tool-result-line"
          :class="[
            resultLineClass,
            {
              'is-file-result': fileArgsInfo,
              'is-file-expanded': fileArgsInfo && (isExpanded || isThisWaitingApproval)
            }
          ]"
        >
          <pre
            v-if="fileArgsInfo && (isExpanded || isThisWaitingApproval)"
            class="tool-result-pre"
          >{{ displayedContent }}</pre>
          <span v-else>{{ resultLine }}</span>
        </div>
      </div>

      <!-- VFS staged badge -->
      <span v-if="exec.vfsState === 'staged' && exec.status === 'success'" class="vfs-staged-badge">staged</span>

      <!-- 审批挂起微章 -->
      <span v-else-if="isThisWaitingApproval" class="approval-pulse-badge">
        <span class="pulse-dot-amber"></span>
        PENDING
      </span>

      <div class="tool-exec-meta" @click.stop>
        <button v-if="hasDetailedContent" class="header-chevron-btn" @click="toggleExpand">
          <svg class="toggle-chevron" :class="{ open: isExpanded || isThisWaitingApproval }" viewBox="0 0 24 24" width="11" height="11" stroke="currentColor" stroke-width="2.5" fill="none">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </button>
      </div>
    </div>


    <!-- 工具折叠体内容 -->
    <div class="tool-exec-body" v-if="(isExpanded || isThisWaitingApproval) && (exec.status === 'error' || isThisWaitingApproval)">
      <!-- 错误状态 -->
      <div class="tool-exec-section is-error" v-if="exec.status === 'error' && exec.error">
        <div class="error-text">{{ exec.error }}</div>
      </div>

      <!-- 💡 顶奢级审批交互面板：磨砂拟态、渐变霓虹呼吸边框与对称排版 -->
      <div class="approval-action-block" v-if="isThisWaitingApproval" @click.stop>
        <div class="approval-message">
          <svg class="warning-icon animate-pulse" viewBox="0 0 24 24" width="14" height="14" stroke="var(--warning-amber)" stroke-width="2" fill="none">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
          <span class="warning-text">安全拦截：该工具操作包含副作用，需要您的授权。</span>
        </div>

        <div class="approval-buttons-row">
          <!-- 拒绝按钮 -->
          <button 
            class="approval-btn reject-btn" 
            :disabled="isProcessingApproval"
            @click="emit('reject', exec.approvalInfo?.approval_id)"
          >
            <span class="btn-hover-glow"></span>
            <span class="btn-text">拒绝 (Reject)</span>
          </button>

          <!-- 全部授权自动运行 -->
          <button 
            class="approval-btn approve-all-btn" 
            :disabled="isProcessingApproval"
            @click="emit('approve-all')"
            title="将权限配置切换为 Full-Auto，本次运行不再拦截任何工具"
          >
            <span class="btn-hover-glow"></span>
            <span class="btn-text">全部授权 (Full Auto)</span>
          </button>

          <!-- 授权单次运行 -->
          <button 
            class="approval-btn approve-btn" 
            :disabled="isProcessingApproval"
            @click="emit('approve', exec.approvalInfo?.approval_id)"
          >
            <span class="btn-hover-glow"></span>
            <span class="btn-text">批准 (Approve)</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ── Claude Code style tool card ── */
.tool-exec-card {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  margin-bottom: 2px;
  position: relative;
  width: 100%;
}

.tool-exec-header {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 3px 0;
  cursor: pointer;
  user-select: none;
  position: relative;
}

/* ── Status prefix symbol ── */
.tool-status-prefix {
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  flex-shrink: 0;
  width: 12px;
  padding-top: 1px;
  text-align: center;
}
.prefix-running  { color: var(--accent-emerald, #34c759); }
.prefix-success  { color: var(--text-muted); opacity: 0.5; }
.prefix-error    { color: var(--text-muted); opacity: 0.55; }
.prefix-approval { color: var(--warning-amber, #FBBF24); }

body.theme-default .tool-exec-card,
body.theme-cyberpunk .tool-exec-card,
body.theme-emerald .tool-exec-card,
body.theme-amber .tool-exec-card {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

.tool-exec-card:hover {
  background: transparent !important;
}

body.theme-default .tool-exec-card:hover,
body.theme-cyberpunk .tool-exec-card:hover,
body.theme-emerald .tool-exec-card:hover,
body.theme-amber .tool-exec-card:hover {
  background: transparent !important;
}

.tool-exec-card.is-expanded {
  background: transparent !important;
  box-shadow: none !important;
}

body.theme-default .tool-exec-card.is-expanded,
body.theme-cyberpunk .tool-exec-card.is-expanded,
body.theme-emerald .tool-exec-card.is-expanded,
body.theme-amber .tool-exec-card.is-expanded {
  background: transparent !important;
  box-shadow: none !important;
}

.tool-exec-card.has-error {
  background: transparent !important;
}

.tool-exec-card.has-error:hover {
  background: transparent !important;
}

.tool-exec-header {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 5px 0;
  cursor: pointer;
  user-select: none;
  position: relative;
}

/* 左侧发光指示线 - 隐藏以求极致自然扁平 */
.tool-status-bar {
  display: none;
}

.tool-exec-icon-box {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: transparent !important;
  border: none !important;
  position: relative;
  transition: all 0.2s ease;
}

body.theme-default .tool-exec-icon-box,
body.theme-cyberpunk .tool-exec-icon-box,
body.theme-emerald .tool-exec-icon-box,
body.theme-amber .tool-exec-icon-box {
  background: transparent !important;
  border: none !important;
}

.tool-exec-icon-box.status-success {
  background: transparent !important;
}

.tool-exec-icon-box.status-running {
  background: transparent !important;
}

.tool-exec-icon-box.status-error {
  background: transparent !important;
}

.tool-exec-name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-mono, monospace);
  flex: 1;
}

.tool-cli-copy {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.tool-cli-main {
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.tool-call-expression {
  min-width: 0;
  font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);
  font-size: 12.5px;
  line-height: 1.4;
  font-weight: 500;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tool-call-expression.status-running {
  color: var(--text-primary);
}

.tool-call-expression.status-success {
  color: var(--text-muted);
  opacity: 0.65;
}

.tool-call-expression.status-error {
  color: var(--text-muted);
  opacity: 0.78;
}

.tool-result-line {
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);
  font-size: 11px;
  line-height: 1.4;
  color: var(--text-muted);
  opacity: 0.7;
  padding-left: 2px;
}

.tool-result-line span:last-child {
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tool-result-line.is-error { color: var(--text-muted); opacity: 0.72; }
.tool-result-line.is-warning { color: var(--warning-amber, #FBBF24); opacity: 1; }
.tool-result-line.is-success { color: var(--text-muted); opacity: 0.55; }
.tool-result-line.is-running { display: none; }

.tool-result-line.is-file-expanded {
  display: block;
  align-items: initial;
  line-height: 1.7;
  opacity: 0.58;
}

.tool-result-pre {
  margin: 0;
  max-height: min(58vh, 640px);
  overflow: auto;
  padding: 0;
  background: transparent;
  border: 0;
  font: inherit;
  color: inherit;
  white-space: pre-wrap;
  word-break: break-word;
}

.tree-elbow {
  color: var(--text-muted);
  flex: 0 0 auto;
}

/* 风趣幽默的展示文字样式覆盖 */
.cute-status-text {
  font-family: var(--font-sans), system-ui, -apple-system, sans-serif !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  letter-spacing: 0px !important;
  color: var(--text-secondary);
  text-transform: none !important;
  transition: color 0.2s ease;
}

.cute-status-text:hover {
  color: var(--text-primary);
}

.cute-status-text.status-error {
  color: var(--danger, #ff453a) !important;
}

.cute-emoji-icon {
  font-size: 13px;
  line-height: 1;
}

.running-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: var(--accent-emerald, #34c759);
  box-shadow: 0 0 8px var(--accent-emerald, #34c759);
  animation: pulse 1.6s infinite ease-in-out;
}

.vfs-staged-badge {
  font-size: 10px;
  font-weight: 600;
  font-family: var(--font-mono, monospace);
  color: var(--warning-amber, #FBBF24);
  background: rgba(251, 191, 36, 0.12);
  padding: 1px 6px;
  border-radius: 4px;
  text-transform: lowercase;
  letter-spacing: 0.3px;
}

.tool-exec-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
  padding-top: 1px;
}

.status-error-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--danger, #ff453a);
  background: rgba(255, 69, 58, 0.12);
  padding: 1px 5px;
  border-radius: 4px;
  font-family: var(--font-mono, monospace);
}

.duration-label {
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono, monospace);
}

.header-chevron-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  border-radius: 4px;
  transition: all 0.2s ease;
  outline: none;
}

.header-chevron-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.toggle-chevron {
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.toggle-chevron.open {
  transform: rotate(180deg);
}

.tool-exec-body {
  border-top: none !important;
  padding: 6px 0 10px 24px;
  background: transparent !important;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

body.theme-default .tool-exec-body,
body.theme-cyberpunk .tool-exec-body,
body.theme-emerald .tool-exec-body,
body.theme-amber .tool-exec-body {
  background: transparent !important;
  border-top-color: transparent !important;
}

.tool-exec-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.error-text {
  padding: 2px 0 4px;
  background: transparent;
  border: 0;
  border-radius: 0;
  font-size: 11px;
  line-height: 1.6;
  color: var(--text-muted);
  opacity: 0.72;
  font-family: var(--font-mono, monospace);
  white-space: pre-wrap;
  word-break: break-all;
}

.tool-exec-group-summary {
  cursor: default;
  opacity: 0.75;
}

.tool-exec-group-summary .tool-exec-header {
  cursor: default;
}

.group-count-badge {
  margin-left: 6px;
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.06);
  padding: 1px 6px;
  border-radius: 10px;
  letter-spacing: 0.02em;
  flex-shrink: 0;
}

/* ── 顶奢审批操作区样式 ── */
.approval-action-block {
  margin-top: 10px;
  padding: 12px 14px;
  border-radius: 6px;
  background: color-mix(in srgb, var(--bg-panel) 96%, var(--text-primary)) !important;
  border: 1px solid var(--border-dim) !important;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  position: relative;
  overflow: hidden;
}

.is-awaiting-approval {
  border-color: var(--accent) !important;
}

.approval-pulse-badge {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  color: var(--accent);
  background: var(--accent-soft);
  padding: 2px 8px;
  border-radius: 10px;
  margin-left: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  letter-spacing: 0.5px;
}

.pulse-dot-amber {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 8px var(--accent);
}

.approval-message {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.warning-text {
  font-size: 12px;
  color: var(--text-secondary);
}

.warning-icon {
  animation: pulse 2s infinite ease-in-out;
}

.approval-buttons-row {
  display: flex;
  gap: 8px;
  width: 100%;
}

.approval-btn {
  flex: 1;
  border: 1px solid var(--border-dim);
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 11px;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  background: transparent;
  color: var(--text-secondary);
}

.approval-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-hover-glow {
  position: absolute;
  top: 0;
  left: -100%;
  width: 300%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
  transition: all 0.6s ease;
}

.approval-btn:hover:not(:disabled) .btn-hover-glow {
  left: 100%;
}

.approval-btn:hover:not(:disabled) {
  background: color-mix(in srgb, var(--text-primary) 5%, transparent);
  color: var(--text-primary);
  border-color: var(--text-muted);
}

/* 拒绝按钮 */
.reject-btn {
  background: transparent;
  color: var(--danger, #ff453a);
  border: 1px solid color-mix(in srgb, var(--danger, #ff453a) 30%, transparent);
}

.reject-btn:hover:not(:disabled) {
  background: color-mix(in srgb, var(--danger, #ff453a) 10%, transparent);
  border-color: var(--danger, #ff453a);
  color: var(--danger, #ff453a);
}

/* 全部授权按钮 */
.approve-all-btn {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-dim);
}

.approve-all-btn:hover:not(:disabled) {
  background: color-mix(in srgb, var(--text-primary) 5%, transparent);
  color: var(--text-primary);
  border-color: var(--text-muted);
}

/* 批准单次运行按钮 */
.approve-btn {
  background: var(--accent, #a66a43);
  color: var(--bg-panel, #ffffff);
  border: 1px solid var(--accent, #a66a43);
}

.approve-btn:hover:not(:disabled) {
  background: color-mix(in srgb, var(--accent, #a66a43) 90%, white);
  border-color: color-mix(in srgb, var(--accent, #a66a43) 90%, white);
  color: var(--bg-panel, #ffffff);
}

@keyframes dotPulse {
  0%, 100% {
    transform: scale(0.9);
    opacity: 0.6;
    box-shadow: 0 0 4px rgba(251, 191, 36, 0.4);
  }
  50% {
    transform: scale(1.15);
    opacity: 1;
    box-shadow: 0 0 10px rgba(251, 191, 36, 0.8);
  }
}

@keyframes cardPulseBorder {
  0%, 100% {
    border-color: rgba(251, 191, 36, 0.15);
  }
  50% {
    border-color: rgba(251, 191, 36, 0.35);
    box-shadow: 0 4px 22px rgba(251, 191, 36, 0.05);
  }
}

@keyframes pulse {
  0%, 100% { opacity: 0.8; }
  50% { opacity: 1; }
}

</style>
