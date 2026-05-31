<script setup lang="ts">
import { computed, ref } from 'vue';
import type { ApprovalInfo } from '../../types';
import ToolIcons from '../common/ToolIcons.vue';

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
  exec: GroupedToolExecution;
  isAwaitingApproval?: boolean;
  pendingApprovalInfo?: ApprovalInfo | null;
  isProcessingApproval?: boolean;
}>();

const emit = defineEmits<{
  (e: 'approve'): void;
  (e: 'reject'): void;
  (e: 'approve-all'): void;
}>();

const isExpanded = ref(false);

const toggleExpand = () => {
  isExpanded.value = !isExpanded.value;
};

const formatJson = (val: any): string => {
  if (typeof val === 'string') {
    try {
      return JSON.stringify(JSON.parse(val), null, 2);
    } catch {
      return val;
    }
  }
  if (val && typeof val === 'object') {
    return JSON.stringify(val, null, 2);
  }
  return String(val);
};

// Check if this specific tool card is currently waiting for approval
const isThisWaitingApproval = computed(() => {
  if (props.exec.status === 'awaiting_approval') return true;
  // Fallback check against pendingApprovalInfo
  if (props.isAwaitingApproval && props.pendingApprovalInfo) {
    const pInfo = props.pendingApprovalInfo;
    const cid = pInfo.tool_call_id;
    if (cid && cid === props.exec.id) return true;
    if (!cid && pInfo.tool_name === props.exec.tool_name) return true;
  }
  return false;
});
</script>

<template>
  <!-- 连续重复调用：紧凑摘要行 -->
  <div
    v-if="exec.groupCount && exec.groupCount > 1"
    class="tool-exec-card tool-exec-group-summary"
  >
    <div class="tool-exec-header">
      <span class="tool-exec-icon-box status-success">
        <ToolIcons :type="exec.tool_name" :size="11" />
      </span>
      <span class="tool-exec-name">{{ exec.tool_name }}</span>
      <span class="group-count-badge">× {{ exec.groupCount }}</span>
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
    <!-- 工具头部 -->
    <div class="tool-exec-header" @click="toggleExpand">
      <span class="tool-exec-icon-box" :class="`status-${isThisWaitingApproval ? 'running' : exec.status}`">
        <ToolIcons :type="exec.tool_name" :size="11" />
      </span>
      <span class="tool-exec-name">{{ exec.tool_name }}</span>
      
      <!-- 运行中状态指示器 -->
      <span v-if="exec.status === 'running'" class="running-indicator">
        <span class="pulse-dot"></span>
      </span>

      <!-- 审批挂起微章 -->
      <span v-else-if="isThisWaitingApproval" class="approval-pulse-badge">
        <span class="pulse-dot-amber"></span>
        PENDING APPROVAL
      </span>

      <div class="tool-exec-meta" @click.stop>
        <span v-if="exec.status === 'error'" class="status-error-label">failed</span>
        <span v-else-if="!isThisWaitingApproval" class="duration-label">{{ exec.duration }}</span>
        
        <button class="header-chevron-btn" @click="toggleExpand">
          <svg class="toggle-chevron" :class="{ open: isExpanded || isThisWaitingApproval }" viewBox="0 0 24 24" width="11" height="11" stroke="currentColor" stroke-width="2.5" fill="none">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- 工具折叠体内容 -->
    <div class="tool-exec-body" v-if="isExpanded || isThisWaitingApproval">
      <!-- 参数 -->
      <div class="tool-exec-section" v-if="exec.args && Object.keys(exec.args).length > 0">
        <div class="section-label">Parameters</div>
        <pre class="json-code"><code>{{ formatJson(exec.args) }}</code></pre>
      </div>

      <!-- 错误状态 -->
      <div class="tool-exec-section is-error" v-if="exec.status === 'error' && exec.error">
        <div class="section-label">Error</div>
        <div class="error-text">{{ exec.error }}</div>
      </div>

      <!-- 正常返回结果 -->
      <div class="tool-exec-section" v-if="exec.status === 'success' && exec.result">
        <div class="section-label">Response</div>
        <pre class="json-code"><code>{{ formatJson(exec.result) }}</code></pre>
      </div>

      <!-- 💡 顶奢级审批交互面板：磨砂拟态、渐变霓虹呼吸边框与对称排版 -->
      <div class="approval-action-block" v-if="isThisWaitingApproval" @click.stop>
        <div class="approval-block-blur"></div>
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
            @click="emit('reject')"
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
            @click="emit('approve')"
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
/* 💡 顶奢毛玻璃立体审批操作区样式 */
.approval-action-block {
  margin-top: 12px;
  padding: 16px;
  border-radius: 8px;
  background: rgba(251, 191, 36, 0.04);
  border: 1px solid rgba(251, 191, 36, 0.15);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  position: relative;
  overflow: hidden;
  animation: cardPulseBorder 3s infinite ease-in-out;
}

.is-awaiting-approval {
  border-color: rgba(251, 191, 36, 0.3) !important;
  box-shadow: 0 0 12px rgba(251, 191, 36, 0.1) !important;
}

.approval-pulse-badge {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  color: var(--warning-amber, #FBBF24);
  background: rgba(251, 191, 36, 0.12);
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
  background: var(--warning-amber, #FBBF24);
  box-shadow: 0 0 8px var(--warning-amber, #FBBF24);
  animation: dotPulse 1.6s infinite ease-in-out;
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
  border: none;
  cursor: pointer;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 11px;
  font-family: var(--font-mono);
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.approval-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 按钮微动效与发光设计 */
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
  transform: translateY(-1px);
}

.approval-btn:active:not(:disabled) {
  transform: translateY(0);
}

/* 拒绝按钮 */
.reject-btn {
  background: rgba(239, 68, 68, 0.1);
  color: #EF4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.reject-btn:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.2);
  box-shadow: 0 0 12px rgba(239, 68, 68, 0.25);
  border-color: rgba(239, 68, 68, 0.5);
}

/* 全部授权按钮 */
.approve-all-btn {
  background: rgba(16, 185, 129, 0.05);
  color: var(--text-secondary);
  border: 1px solid var(--border-dim);
}

.approve-all-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
  border-color: var(--text-muted);
}

/* 批准单次运行按钮 */
.approve-btn {
  background: rgba(16, 185, 129, 0.15);
  color: #10B981;
  border: 1px solid rgba(16, 185, 129, 0.35);
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.1);
}

.approve-btn:hover:not(:disabled) {
  background: rgba(16, 185, 129, 0.25);
  box-shadow: 0 0 15px rgba(16, 185, 129, 0.35);
  border-color: rgba(16, 185, 129, 0.6);
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
  transition: all 0.15s ease;
}

.header-chevron-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
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
