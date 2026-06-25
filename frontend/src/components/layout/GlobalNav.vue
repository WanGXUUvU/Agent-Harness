<script setup lang="ts">
defineProps<{
  activeView: string;
}>();

const emit = defineEmits<{
  (e: 'update:activeView', view: string): void;
  (e: 'action', action: string): void;
}>();

const actionItems = [
  { id: 'plugins', action: 'open-plugins', label: 'Plugins', tooltip: 'MCP 插件市场', svg: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="1.5" fill="none"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>` },
  { id: 'agents', action: 'open-agents', label: 'Agents', tooltip: '自定义 Agent', svg: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="1.5" fill="none"><circle cx="12" cy="8" r="4"></circle><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"></path><circle cx="18" cy="8" r="2.5"></circle><path d="M20.5 15c1.5.5 2.5 1.8 2.5 3.5"></path></svg>` },
  { id: 'settings', action: 'open-settings', label: 'Settings', tooltip: '设置 & 模型', svg: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="1.5" fill="none"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>` },
];
</script>

<template>
  <nav class="global-nav">
    <!-- Logo -->
    <div class="nav-top">
      <div class="logo" title="Ariadne">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="var(--accent)" stroke="none"><polygon points="12 2 2 22 22 22"></polygon></svg>
      </div>
    </div>

    <!-- 操作区 -->
    <div class="nav-section nav-actions-section">
      <div class="nav-section-label">TOOLS</div>
      <div class="nav-group">
        <button
          v-for="item in actionItems"
          :key="item.id"
          class="nav-item"
          :title="item.tooltip"
          @click="emit('action', item.action)"
        >
          <span class="nav-icon" v-html="item.svg"></span>
        </button>
      </div>
    </div>

    <!-- 底部用户 -->
    <div class="nav-bottom">
      <div class="user-avatar" title="User">
        <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
      </div>
    </div>
  </nav>
</template>

<style scoped>
.global-nav {
  align-items: center;
  padding: 12px 0;
  justify-content: space-between;
  gap: 0;
}

.nav-top {
  display: flex;
  justify-content: center;
  padding-bottom: 8px;
}

.logo {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  padding: 8px 0;
}

.nav-section-label {
  font-size: 8px;
  font-family: var(--font-mono, monospace);
  letter-spacing: 0.1em;
  color: var(--text-muted);
  margin-bottom: 6px;
  opacity: 0.6;
}

.nav-actions-section {
  flex: 1;
}

.nav-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
}

.nav-item {
  position: relative;
  width: calc(100% - 16px);
  margin: 0 8px;
  height: 40px;
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  transition: color 0.2s ease, background 0.2s ease;
  border-radius: 8px;
}

.nav-item:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 0;
}

.nav-bottom {
  display: flex;
  justify-content: center;
  padding-top: 8px;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-dim);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  background: var(--bg-hover);
  transition: var(--transition-fast);
  cursor: pointer;
}

.user-avatar:hover {
  border-color: var(--border-strong);
  color: var(--text-primary);
}
</style>
