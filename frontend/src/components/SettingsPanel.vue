<script setup lang="ts">
/**
 * SettingsPanel.vue
 * 职责：模型 Provider 管理与模型设置启用面板 (Codex 侧边栏风格升级)
 * 不负责：对话逻辑与会话管理
 */
import { ref, onMounted, watch, computed } from 'vue';
import { settingsApi } from '../api/settings';
import type { Provider, ModelSetting } from '../api/settings';

const props = defineProps<{
  isOpen: boolean;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

// ── 导航与标签页管理 ──
const activeTab = ref('general');

const TABS = [
  { id: 'general', name: '常规' },
  { id: 'profile', name: '个人资料' },
  { id: 'appearance', name: '外观' },
  { id: 'snapshots', name: '应用快照' },
  { id: 'providers', name: '配置' },
  { id: 'customization', name: '个性化' },
  { id: 'shortcuts', name: '键盘快捷键' },
  { id: 'mcp', name: 'MCP 服务器' },
  { id: 'hooks', name: '钩子' },
  { id: 'connections', name: '连接' },
  { id: 'git', name: 'Git' },
  { id: 'environment', name: '环境' },
  { id: 'worktree', name: '工作树' },
  { id: 'browser', name: '浏览器' },
  { id: 'computer', name: '电脑操控' },
  { id: 'archive', name: '已归档对话' },
  { id: 'billing', name: '使用情况和计费' },
] as const;

const currentTabName = computed(() => {
  const t = TABS.find(tab => tab.id === activeTab.value);
  return t ? t.name : '设置';
});

// ── 常规设置状态 (基于 localStorage 实现真实功能) ──
const settingsGeneral = ref({
  autoSave: localStorage.getItem('settings-auto-save') !== 'false',
  sendShortcut: localStorage.getItem('settings-send-shortcut') || 'Enter',
  sidebarFoldersOpen: localStorage.getItem('settings-sidebar-folders') !== 'false',
  streamDelay: parseInt(localStorage.getItem('settings-stream-delay') || '10'),
  autoCompact: localStorage.getItem('settings-auto-compact') === 'true',
});

const saveGeneralSettings = () => {
  localStorage.setItem('settings-auto-save', String(settingsGeneral.value.autoSave));
  localStorage.setItem('settings-send-shortcut', settingsGeneral.value.sendShortcut);
  localStorage.setItem('settings-sidebar-folders', String(settingsGeneral.value.sidebarFoldersOpen));
  localStorage.setItem('settings-stream-delay', String(settingsGeneral.value.streamDelay));
  localStorage.setItem('settings-auto-compact', String(settingsGeneral.value.autoCompact));
};

watch(settingsGeneral, () => {
  saveGeneralSettings();
}, { deep: true });

// ── 状态管理 ──
const providers = ref<Provider[]>([]);
const modelsByProvider = ref<Record<number, ModelSetting[]>>({});
const expandedProviders = ref<Record<number, boolean>>({});
const syncingProviders = ref<Record<number, boolean>>({});
const isLoading = ref(true);
const showAddForm = ref(false);
const errorMsg = ref<string | null>(null);

// 编辑 Provider
const editingProviderId = ref<number | null>(null);
const editForm = ref({ name: '', base_url: '', api_key: '' });

// 新增 Provider 表单数据
const newProvider = ref({
  name: '',
  base_url: '',
  api_key: '',
});

// ── 行为方法 ──

// 加载所有 Provider 及其对应的 ModelSettings
const loadAllData = async () => {
  try {
    isLoading.value = true;
    errorMsg.value = null;
    const provs = await settingsApi.listProviders();
    providers.value = provs;
  } catch (err: any) {
    errorMsg.value = '加载 Provider 列表失败: ' + err.message;
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  if (props.isOpen) {
    loadAllData();
  }
});

// ── 监听 isOpen，开启时自动拉取数据 ──
watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    loadAllData();
  }
});

// 开始编辑某个 Provider
const startEditProvider = (prov: Provider) => {
  editingProviderId.value = prov.id;
  editForm.value = { name: prov.name, base_url: prov.base_url, api_key: '' };
};

// 取消编辑
const cancelEditProvider = () => {
  editingProviderId.value = null;
};

// 保存编辑
const handleSaveEdit = async (providerId: number) => {
  const patch: { name?: string; base_url?: string; api_key?: string } = {};
  if (editForm.value.name) patch.name = editForm.value.name;
  if (editForm.value.base_url) patch.base_url = editForm.value.base_url;
  if (editForm.value.api_key) patch.api_key = editForm.value.api_key;
  try {
    errorMsg.value = null;
    const updated = await settingsApi.patchProvider(providerId, patch);
    const idx = providers.value.findIndex(p => p.id === providerId);
    if (idx !== -1) providers.value[idx] = updated;
    editingProviderId.value = null;
  } catch (err: any) {
    errorMsg.value = '更新服务商失败: ' + err.message;
  }
};

// 展开/折叠 Provider 卡片，并自动同步/加载模型
const toggleExpandProvider = async (providerId: number) => {
  expandedProviders.value[providerId] = !expandedProviders.value[providerId];
  if (expandedProviders.value[providerId] && !modelsByProvider.value[providerId]) {
    await handleSyncModels(providerId);
  }
};

// 同步 Provider 模型列表
const handleSyncModels = async (providerId: number) => {
  try {
    syncingProviders.value[providerId] = true;
    errorMsg.value = null;
    const models = await settingsApi.syncModels(providerId);
    modelsByProvider.value[providerId] = models;
    expandedProviders.value[providerId] = true;
  } catch (err: any) {
    errorMsg.value = `同步模型失败: ${err.message}`;
  } finally {
    syncingProviders.value[providerId] = false;
  }
};

// 创建新 Provider
const handleCreateProvider = async () => {
  if (!newProvider.value.name || !newProvider.value.base_url) {
    errorMsg.value = '请填写 Provider 名称和 API Base URL';
    return;
  }
  try {
    errorMsg.value = null;
    const created = await settingsApi.createProvider({
      name: newProvider.value.name,
      base_url: newProvider.value.base_url,
      api_key: newProvider.value.api_key,
    });
    providers.value.push(created);
    newProvider.value = { name: '', base_url: '', api_key: '' };
    showAddForm.value = false;
    await toggleExpandProvider(created.id);
  } catch (err: any) {
    errorMsg.value = '创建 Provider 失败: ' + err.message;
  }
};

// 删除 Provider
const handleDeleteProvider = async (id: number) => {
  if (!confirm('确定要删除此 Provider 吗？这将同时删除该 Provider 下的所有模型设置。')) return;
  try {
    errorMsg.value = null;
    await settingsApi.deleteProvider(id);
    providers.value = providers.value.filter(p => p.id !== id);
    delete modelsByProvider.value[id];
    delete expandedProviders.value[id];
  } catch (err: any) {
    errorMsg.value = '删除 Provider 失败: ' + err.message;
  }
};

// 切换模型启用状态
const toggleModelEnabled = async (model: ModelSetting, providerId: number) => {
  const originalState = model.enabled;
  model.enabled = !model.enabled;
  try {
    await settingsApi.patchModel(model.id, { enabled: model.enabled });
  } catch (err: any) {
    model.enabled = originalState;
    errorMsg.value = `更新模型状态失败: ${err.message}`;
  }
};

// 修改模型显示名称
const updateModelDisplayName = async (model: ModelSetting, newName: string) => {
  const originalName = model.display_name;
  model.display_name = newName;
  try {
    await settingsApi.patchModel(model.id, { display_name: newName });
  } catch (err: any) {
    model.display_name = originalName;
    errorMsg.value = `更新模型显示名称失败: ${err.message}`;
  }
};

// 设为默认服务商
const handleSetDefault = async (providerId: number) => {
  const previousProviders = providers.value.map(p => ({ ...p }));
  providers.value = providers.value.map(p => ({
    ...p,
    is_default: p.id === providerId,
  }));
  try {
    errorMsg.value = null;
    await settingsApi.setDefaultProvider(providerId);
  } catch (err: any) {
    providers.value = previousProviders;
    errorMsg.value = '设置默认服务商失败: ' + err.message;
  }
};

// ── 主题管理 ──
const THEMES = [
  { id: 'default', name: '深空墨黑', colors: ['#000000', '#111111', '#FFFFFF'] },
  { id: 'cyberpunk', name: '赛博魅紫', colors: ['#090514', '#171133', '#A78BFA'] },
  { id: 'emerald', name: '翡翠森林', colors: ['#040D0A', '#112C22', '#10B981'] },
  { id: 'amber', name: '琥珀古金', colors: ['#0D0C0A', '#2E281F', '#F59E0B'] },
  { id: 'light-apple', name: '苹果极简 (雅白)', colors: ['#F5F5F7', '#FFFFFF', '#0071E3'] },
  { id: 'light-openai', name: 'OpenAI (素绿)', colors: ['#F9F9F9', '#FFFFFF', '#10A37F'] },
] as const;

const currentTheme = ref(localStorage.getItem('agent-build-theme') || 'default');

const selectTheme = (themeId: string) => {
  currentTheme.value = themeId;
  document.body.className = `theme-${themeId}`;
  localStorage.setItem('agent-build-theme', themeId);
};

// ── MCP 服务器交互状态 ──
const mcpTerminalVisible = ref(false);
</script>

<template>
  <div v-if="isOpen" class="marketplace-modal-overlay" @click.self="$emit('close')">
    <div class="settings-modal">
      
      <!-- 🟢 左侧：顶奢毛玻璃导航侧边栏 -->
      <aside class="settings-sidebar">
        <!-- macOS 窗口控制红黄绿三色点 -->
        <div class="window-controls">
          <span class="control-dot close" @click="$emit('close')" title="关闭设置"></span>
          <span class="control-dot minimize"></span>
          <span class="control-dot maximize"></span>
        </div>

        <!-- 返回应用触发器 -->
        <div class="back-to-app-btn" @click="$emit('close')">
          <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2.5" fill="none" class="back-arrow-icon">
            <line x1="19" y1="12" x2="5" y2="12"></line>
            <polyline points="12 19 5 12 12 5"></polyline>
          </svg>
          <span class="back-text">返回应用</span>
        </div>

        <!-- 垂直滚动的设置项列表 -->
        <nav class="sidebar-nav">
          <button 
            v-for="tab in TABS" 
            :key="tab.id"
            class="nav-item"
            :class="{ active: activeTab === tab.id }"
            @click="activeTab = tab.id"
          >
            <span class="active-bar" v-if="activeTab === tab.id"></span>
            <svg class="nav-icon" viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none">
              <template v-if="tab.id === 'general'">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
              </template>
              <template v-else-if="tab.id === 'profile'">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </template>
              <template v-else-if="tab.id === 'appearance'">
                <circle cx="12" cy="12" r="10"></circle>
                <path d="M12 2v20"></path>
                <path d="M12 6a6 6 0 0 1 6 6 6 6 0 0 1-6 6"></path>
              </template>
              <template v-else-if="tab.id === 'snapshots'">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <circle cx="9" cy="9" r="2"></circle>
                <path d="M21 15l-3.086-3.086a2 2 0 0 0-2.828 0L6 21"></path>
              </template>
              <template v-else-if="tab.id === 'providers'">
                <line x1="4" y1="21" x2="4" y2="14"></line>
                <line x1="4" y1="10" x2="4" y2="3"></line>
                <line x1="12" y1="21" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12" y2="3"></line>
                <line x1="20" y1="21" x2="20" y2="16"></line>
                <line x1="20" y1="12" x2="20" y2="3"></line>
                <line x1="1" y1="14" x2="7" y2="14"></line>
                <line x1="9" y1="8" x2="15" y2="8"></line>
                <line x1="17" y1="16" x2="23" y2="16"></line>
              </template>
              <template v-else-if="tab.id === 'customization'">
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"></path>
              </template>
              <template v-else-if="tab.id === 'shortcuts'">
                <rect x="2" y="4" width="20" height="16" rx="2" ry="2"></rect>
                <line x1="6" y1="8" x2="6" y2="8"></line>
                <line x1="10" y1="8" x2="10" y2="8"></line>
                <line x1="14" y1="8" x2="14" y2="8"></line>
                <line x1="18" y1="8" x2="18" y2="8"></line>
                <line x1="6" y1="12" x2="6" y2="12"></line>
                <line x1="10" y1="12" x2="10" y2="12"></line>
                <line x1="14" y1="12" x2="14" y2="12"></line>
                <line x1="18" y1="12" x2="18" y2="12"></line>
                <line x1="7" y1="16" x2="17" y2="16"></line>
              </template>
              <template v-else-if="tab.id === 'mcp'">
                <path d="M18 8h1a4 4 0 0 1 0 8h-1"></path>
                <path d="M2 8h16v8H2z"></path>
                <line x1="6" y1="1" x2="6" y2="4"></line>
                <line x1="10" y1="1" x2="10" y2="4"></line>
                <line x1="14" y1="1" x2="14" y2="4"></line>
              </template>
              <template v-else-if="tab.id === 'hooks'">
                <path d="M18 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3 3 3 0 0 0 3-3V6a3 3 0 0 0-3-3z"></path>
                <path d="M6 21a3 3 0 0 0 3-3V6a3 3 0 0 0-3-3 3 3 0 0 0-3 3v12a3 3 0 0 0 3 3z"></path>
              </template>
              <template v-else-if="tab.id === 'connections'">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="2" y1="12" x2="22" y2="12"></line>
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
              </template>
              <template v-else-if="tab.id === 'git'">
                <circle cx="18" cy="18" r="3"></circle>
                <circle cx="6" cy="6" r="3"></circle>
                <circle cx="6" cy="18" r="3"></circle>
                <line x1="6" y1="9" x2="6" y2="15"></line>
                <path d="M9 18h3a6 6 0 0 0 6-6V9"></path>
              </template>
              <template v-else-if="tab.id === 'environment'">
                <polyline points="4 17 10 11 4 5"></polyline>
                <line x1="12" y1="19" x2="20" y2="19"></line>
              </template>
              <template v-else-if="tab.id === 'worktree'">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                <line x1="12" y1="11" x2="12" y2="17"></line>
                <line x1="9" y1="14" x2="15" y2="14"></line>
              </template>
              <template v-else-if="tab.id === 'browser'">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                <line x1="2" y1="10" x2="22" y2="10"></line>
                <line x1="12" y1="17" x2="12" y2="21"></line>
                <line x1="7" y1="21" x2="17" y2="21"></line>
              </template>
              <template v-else-if="tab.id === 'computer'">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                <line x1="8" y1="21" x2="16" y2="21"></line>
                <line x1="12" y1="17" x2="12" y2="21"></line>
              </template>
              <template v-else-if="tab.id === 'archive'">
                <polyline points="21 8 21 21 3 21 3 8"></polyline>
                <rect x="1" y="3" width="22" height="5"></rect>
                <line x1="10" y1="12" x2="14" y2="12"></line>
              </template>
              <template v-else-if="tab.id === 'billing'">
                <rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect>
                <line x1="1" y1="10" x2="23" y2="10"></line>
              </template>
            </svg>
            <span class="nav-label">{{ tab.name }}</span>
          </button>
        </nav>
      </aside>

      <!-- 🔵 右侧：主设置面板内容区 -->
      <main class="settings-content">
        <!-- 头部标题与直接关闭按钮 -->
        <header class="content-header">
          <h2>{{ currentTabName }}</h2>
          <button class="close-btn-right" @click="$emit('close')">
            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2.5" fill="none">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </header>

        <!-- 主体区域 -->
        <div class="content-body">
          <!-- 错误提示组件 -->
          <div v-if="errorMsg" class="settings-error">
            <span>{{ errorMsg }}</span>
            <button @click="errorMsg = null">✕</button>
          </div>

          <!-- 1. 常规配置面板 (General Settings) -->
          <div v-if="activeTab === 'general'" class="settings-panel-view">
            <div class="view-description">基础常规设置，直接保存至本地。</div>
            <div class="settings-group">
              <div class="settings-row">
                <div class="row-info">
                  <div class="row-title">自动保存历史记录</div>
                  <div class="row-desc">自动将您的对话会话和历史保存到本地持久化。</div>
                </div>
                <button class="switch-toggle" :class="{ active: settingsGeneral.autoSave }" @click="settingsGeneral.autoSave = !settingsGeneral.autoSave">
                  <span class="switch-dot"></span>
                </button>
              </div>

              <div class="settings-row">
                <div class="row-info">
                  <div class="row-title">发送消息快捷键</div>
                  <div class="row-desc">选择在输入框中提交对话时使用的快捷键组合。</div>
                </div>
                <select v-model="settingsGeneral.sendShortcut" class="premium-select">
                  <option value="Enter">Enter 发送 / Shift+Enter 换行</option>
                  <option value="CmdEnter">Cmd+Enter 发送 / Enter 换行</option>
                </select>
              </div>

              <div class="settings-row">
                <div class="row-info">
                  <div class="row-title">侧边栏文件夹默认展开</div>
                  <div class="row-desc">在加载应用时默认保持工作区组文件夹处于展开状态。</div>
                </div>
                <button class="switch-toggle" :class="{ active: settingsGeneral.sidebarFoldersOpen }" @click="settingsGeneral.sidebarFoldersOpen = !settingsGeneral.sidebarFoldersOpen">
                  <span class="switch-dot"></span>
                </button>
              </div>

              <div class="settings-row">
                <div class="row-info">
                  <div class="row-title">打字机效果延迟 ({{ settingsGeneral.streamDelay }}ms)</div>
                  <div class="row-desc">调整 AI 流式生成文本时的逐字展现延迟。</div>
                </div>
                <input v-model.number="settingsGeneral.streamDelay" type="range" min="0" max="100" step="5" class="premium-slider" />
              </div>

              <div class="settings-row">
                <div class="row-info">
                  <div class="row-title">智能令牌压缩 (Token Auto-compaction)</div>
                  <div class="row-desc">当会话超过模型的 80% 上下文时，自动触发后端精简压缩。</div>
                </div>
                <button class="switch-toggle" :class="{ active: settingsGeneral.autoCompact }" @click="settingsGeneral.autoCompact = !settingsGeneral.autoCompact">
                  <span class="switch-dot"></span>
                </button>
              </div>
            </div>
          </div>

          <!-- 2. 外观主题配置面板 (Appearance / Theme) -->
          <div v-if="activeTab === 'appearance'" class="settings-panel-view">
            <div class="view-description">界面主题配色方案，即时切换全身变装。</div>
            <div class="theme-grid">
              <button
                v-for="t in THEMES"
                :key="t.id"
                class="theme-card"
                :class="{ active: currentTheme === t.id }"
                @click="selectTheme(t.id)"
              >
                <div class="theme-card-preview">
                  <span v-for="c in t.colors" :key="c" class="preview-dot" :style="{ background: c }"></span>
                </div>
                <span class="theme-card-name">{{ t.name }}</span>
              </button>
            </div>
          </div>

          <!-- 3. AI 服务商及模型列表 (Providers & Models Config) -->
          <div v-if="activeTab === 'providers'" class="settings-panel-view">
            <div class="view-description">配置 AI 服务商提供商，并同步及激活其支持的所有模型。</div>
            
            <!-- 加载状态 -->
            <div v-if="isLoading" class="loading-state">
              <span>正在加载服务商列表...</span>
            </div>

            <div v-else class="provider-list">
              <!-- Configuration Header & Add Provider Toggle Card -->
              <div class="provider-card ghost-add-card" :class="{ 'form-open': showAddForm }">
                <div class="ghost-card-trigger" @click="showAddForm = !showAddForm">
                  <span class="ghost-icon">{{ showAddForm ? '✕' : '＋' }}</span>
                  <span class="ghost-text">{{ showAddForm ? '关闭新增表单' : '配置并新增 AI 服务商 (Add Provider)' }}</span>
                </div>

                <!-- Inline Add Form -->
                <Transition name="expand">
                  <div v-if="showAddForm" class="add-provider-inline-form">
                    <div class="form-grid">
                      <div class="form-group">
                        <label>服务商自定义名称</label>
                        <input v-model="newProvider.name" type="text" placeholder="例如: DeepSeek, OpenAI, Ollama" />
                      </div>
                      <div class="form-group">
                        <label>API Base URL</label>
                        <input v-model="newProvider.base_url" type="text" placeholder="https://api.deepseek.com/v1" />
                      </div>
                      <div class="form-group">
                        <label>API Key (密钥)</label>
                        <input v-model="newProvider.api_key" type="password" placeholder="sk-..." />
                      </div>
                    </div>
                    <div class="form-actions">
                      <button class="save-btn" @click="handleCreateProvider">保存并初始化服务商</button>
                    </div>
                  </div>
                </Transition>
              </div>

              <!-- Real Provider list -->
              <div v-for="prov in providers" :key="prov.id" class="provider-card">
                <!-- Header -->
                <div class="provider-card-header" @click="toggleExpandProvider(prov.id)">
                  <div class="prov-info">
                    <span class="prov-name">{{ prov.name }}</span>
                    <span class="prov-url">{{ prov.base_url }}</span>
                    <span v-if="prov.api_key_hint" class="prov-key-hint">{{ prov.api_key_hint }}</span>
                  </div>
                  <div class="prov-actions" @click.stop>
                    <button
                      class="star-icon-btn"
                      :class="{ active: prov.is_default }"
                      @click="handleSetDefault(prov.id)"
                      :title="prov.is_default ? '默认服务商' : '设为默认服务商'"
                    >
                      <svg viewBox="0 0 24 24" width="13" height="13" stroke="currentColor" stroke-width="2.5" fill="none" class="star-icon">
                        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                      </svg>
                    </button>
                    <button
                      class="edit-icon-btn"
                      @click="startEditProvider(prov)"
                      title="编辑服务商信息"
                    >
                      <svg viewBox="0 0 24 24" width="13" height="13" stroke="currentColor" stroke-width="2.5" fill="none">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                      </svg>
                    </button>
                    <button
                      class="sync-btn"
                      :disabled="syncingProviders[prov.id]"
                      @click="handleSyncModels(prov.id)"
                      title="拉取并同步服务商的所有模型"
                    >
                      <svg class="sync-icon" :class="{ spinning: syncingProviders[prov.id] }" viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="2.5" fill="none">
                        <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
                      </svg>
                      {{ syncingProviders[prov.id] ? '同步中…' : '同步模型' }}
                    </button>
                    <button class="delete-icon-btn" @click="handleDeleteProvider(prov.id)" title="删除服务商">
                      <svg viewBox="0 0 24 24" width="13" height="13" stroke="currentColor" stroke-width="2.5" fill="none">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                      </svg>
                    </button>
                    <svg class="expand-chevron" :class="{ open: expandedProviders[prov.id] }" viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="2.5" fill="none">
                      <polyline points="6 9 12 15 18 9"/>
                    </svg>
                  </div>
                </div>

                <!-- Inline Edit Form -->
                <Transition name="expand">
                  <div v-if="editingProviderId === prov.id" class="edit-provider-form" @click.stop>
                    <div class="form-grid">
                      <div class="form-group">
                        <label>服务商名称</label>
                        <input v-model="editForm.name" type="text" :placeholder="prov.name" />
                      </div>
                      <div class="form-group">
                        <label>API Base URL</label>
                        <input v-model="editForm.base_url" type="text" :placeholder="prov.base_url" />
                      </div>
                      <div class="form-group">
                        <label>API Key（留空保持不变）</label>
                        <input v-model="editForm.api_key" type="password" placeholder="输入新 Key 或留空" />
                      </div>
                    </div>
                    <div class="form-actions">
                      <button class="save-btn" @click="handleSaveEdit(prov.id)">保存</button>
                      <button class="cancel-btn" @click="cancelEditProvider">取消</button>
                    </div>
                  </div>
                </Transition>

                <!-- Model Settings Table -->
                <Transition name="expand">
                  <div v-if="expandedProviders[prov.id]" class="provider-models-wrapper">
                    <div v-if="syncingProviders[prov.id] && !modelsByProvider[prov.id]" class="models-loading">
                      正在加载并同步模型中...
                    </div>
                    <div v-else-if="!modelsByProvider[prov.id] || modelsByProvider[prov.id].length === 0" class="models-empty">
                      暂未同步任何模型，请点击右上方“同步模型”按钮。
                    </div>
                    <table v-else class="models-table">
                      <thead>
                        <tr>
                          <th>模型 ID</th>
                          <th>显示名称</th>
                          <th>上下文</th>
                          <th>能力标签</th>
                          <th style="text-align: right; width: 80px;">启用</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="model in modelsByProvider[prov.id]" :key="model.id" :class="{ disabled: !model.enabled }">
                          <td class="td-model-id mono-text">{{ model.model_id }}</td>
                          <td class="td-display-name">
                            <input
                              :value="model.display_name || model.model_id"
                              @change="e => updateModelDisplayName(model, (e.target as HTMLInputElement).value)"
                              class="model-name-input"
                              type="text"
                              title="修改以更新显示名称"
                            />
                          </td>
                          <td class="td-ctx mono-text">
                            {{ model.context_length ? `${Math.round(model.context_length / 1024)}K` : '-' }}
                          </td>
                          <td class="td-tags">
                            <span v-if="model.supports_thinking" class="cap-tag badge-thinking" title="支持深度思考">
                              🧠 思考
                            </span>
                            <span v-if="model.supports_tools" class="cap-tag badge-tools" title="支持 Tool Calling">
                              🔧 工具
                            </span>
                          </td>
                          <td style="text-align: right;">
                            <button
                              class="switch-toggle"
                              :class="{ active: model.enabled }"
                              @click="toggleModelEnabled(model, prov.id)"
                            >
                              <span class="switch-dot"></span>
                            </button>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </Transition>
              </div>
            </div>
          </div>

          <!-- 4. MCP 服务器配置面板 (MCP Servers Dashboard) -->
          <div v-if="activeTab === 'mcp'" class="settings-panel-view">
            <div class="view-description">查看及装配本地 Model Context Protocol (MCP) 服务器以自动扩展 Agent 的工具箱。</div>
            
            <div class="mcp-servers-list">
              <div class="mcp-server-card">
                <div class="card-header-main">
                  <div class="server-meta">
                    <span class="server-dot active"></span>
                    <span class="server-name">filesystem-server</span>
                    <span class="server-type">标准本地服务</span>
                  </div>
                  <span class="server-status active">已连接</span>
                </div>
                <div class="server-body">
                  <div class="server-detail-row">
                    <span class="detail-label">启动指令:</span>
                    <span class="detail-val mono-text">npx -y @modelcontextprotocol/server-filesystem /Users/wangxu/Documents/AGENT Build</span>
                  </div>
                  <div class="server-detail-row">
                    <span class="detail-label">提供的工具:</span>
                    <div class="tool-badges">
                      <span class="tool-badge">read_file</span>
                      <span class="tool-badge">write_file</span>
                      <span class="tool-badge">list_dir</span>
                      <span class="tool-badge">grep_search</span>
                    </div>
                  </div>
                </div>
              </div>

              <div class="mcp-server-card">
                <div class="card-header-main">
                  <div class="server-meta">
                    <span class="server-dot active"></span>
                    <span class="server-name">tavily-search-server</span>
                    <span class="server-type">Web 外部集成</span>
                  </div>
                  <span class="server-status active">已连接</span>
                </div>
                <div class="server-body">
                  <div class="server-detail-row">
                    <span class="detail-label">运行模块:</span>
                    <span class="detail-val mono-text">python -m mcp_tavily</span>
                  </div>
                  <div class="server-detail-row">
                    <span class="detail-label">提供的工具:</span>
                    <div class="tool-badges">
                      <span class="tool-badge">web_search</span>
                      <span class="tool-badge">fetch_page</span>
                    </div>
                  </div>
                </div>
              </div>

              <div class="mcp-server-card">
                <div class="card-header-main">
                  <div class="server-meta">
                    <span class="server-dot active"></span>
                    <span class="server-name">sandbox-interpreter</span>
                    <span class="server-type">代码执行沙箱</span>
                  </div>
                  <span class="server-status active">已连接</span>
                </div>
                <div class="server-body">
                  <div class="server-detail-row">
                    <span class="detail-label">API 端口:</span>
                    <span class="detail-val mono-text">http://localhost:8888</span>
                  </div>
                  <div class="server-detail-row">
                    <span class="detail-label">提供的工具:</span>
                    <div class="tool-badges">
                      <span class="tool-badge">execute_python</span>
                      <span class="tool-badge">install_package</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Interactive Terminal Console Mock -->
            <div class="mcp-terminal-section">
              <div class="terminal-header" @click="mcpTerminalVisible = !mcpTerminalVisible">
                <div class="term-left">
                  <span class="terminal-icon">$_</span>
                  <span>服务器控制台实时输出 (Terminal Logs)</span>
                </div>
                <span class="chevron" :class="{ open: mcpTerminalVisible }">▼</span>
              </div>
              <div v-if="mcpTerminalVisible" class="terminal-body mono-text">
                <div class="log-line">`[23:28:10] [mcp/filesystem] starting process...`</div>
                <div class="log-line">`[23:28:12] [mcp/filesystem] filesystem is now listening on stdio. path="/Users/wangxu/Documents/AGENT Build"`</div>
                <div class="log-line">`[23:28:14] [mcp/websearch] tavily initialized. query limit = 1000/day`</div>
                <div class="log-line success">`[23:28:15] [mcp/manager] 3 servers connected successfully. 8 tools loaded.`</div>
              </div>
            </div>
          </div>

          <!-- 5. 键盘快捷键面板 (Keyboard Shortcuts Reference Sheet) -->
          <div v-if="activeTab === 'shortcuts'" class="settings-panel-view">
            <div class="view-description">键盘快捷操作手册，极大提升您的操控效率。</div>
            <div class="shortcuts-table">
              <div class="shortcut-item">
                <span class="shortcut-name">新建助理对话会话</span>
                <span class="shortcut-keys"><kbd>⌘</kbd> + <kbd>J</kbd></span>
              </div>
              <div class="shortcut-item">
                <span class="shortcut-name">新建编码对话会话</span>
                <span class="shortcut-keys"><kbd>⌘</kbd> + <kbd>K</kbd></span>
              </div>
              <div class="shortcut-item">
                <span class="shortcut-name">折叠/展开主侧边栏</span>
                <span class="shortcut-keys"><kbd>⌘</kbd> + <kbd>\</kbd> 或 <kbd>⌘</kbd> + <kbd>B</kbd></span>
              </div>
              <div class="shortcut-item">
                <span class="shortcut-name">打开模型与全局设置</span>
                <span class="shortcut-keys"><kbd>⌘</kbd> + <kbd>,</kbd></span>
              </div>
              <div class="shortcut-item">
                <span class="shortcut-name">向 Agent 提交当前指令</span>
                <span class="shortcut-keys"><kbd>Enter</kbd> 或 <kbd>⌘</kbd> + <kbd>Enter</kbd></span>
              </div>
              <div class="shortcut-item">
                <span class="shortcut-name">关闭弹出窗口 / 返回应用</span>
                <span class="shortcut-keys"><kbd>Esc</kbd></span>
              </div>
            </div>
          </div>

          <!-- 6. 使用情况和计费面板 (Usage & Billing Dashboard) -->
          <div v-if="activeTab === 'billing'" class="settings-panel-view">
            <div class="view-description">监控模型调用总频次、本地和云端资源的总 Token 消费数额。</div>
            
            <div class="billing-dash">
              <div class="billing-card-mini">
                <div class="mini-title">账户层级</div>
                <div class="mini-value highlight-cyan">Free Developer</div>
                <div class="mini-subtitle">本地免费模式 / 无限免费</div>
              </div>
              <div class="billing-card-mini">
                <div class="mini-title">本周 API 请求数</div>
                <div class="mini-value text-accent">1,280 次</div>
                <div class="mini-subtitle">调用高峰：昨日 (540次)</div>
              </div>
            </div>

            <!-- Token progress bar -->
            <div class="progress-section">
              <div class="progress-labels">
                <span>月度 Token 使用量限制</span>
                <span class="mono-text">76.5% (1.53M / 2.0M tokens)</span>
              </div>
              <div class="progress-track">
                <div class="progress-bar-fill" style="width: 76.5%"></div>
              </div>
            </div>

            <!-- CSS Bar Chart -->
            <div class="chart-section">
              <div class="chart-header">每日 API 消耗趋势</div>
              <div class="bar-chart-container">
                <div class="bar-col">
                  <div class="bar-fill" style="height: 50%" title="周一: 350次"></div>
                  <span class="bar-label">Mon</span>
                </div>
                <div class="bar-col">
                  <div class="bar-fill" style="height: 70%" title="周二: 480次"></div>
                  <span class="bar-label">Tue</span>
                </div>
                <div class="bar-col">
                  <div class="bar-fill" style="height: 90%" title="周三: 620次"></div>
                  <span class="bar-label">Wed</span>
                </div>
                <div class="bar-col">
                  <div class="bar-fill" style="height: 30%" title="周四: 210次"></div>
                  <span class="bar-label">Thu</span>
                </div>
                <div class="bar-col active">
                  <div class="bar-fill active" style="height: 78%" title="周五 (今日): 540次"></div>
                  <span class="bar-label">Fri</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 7. 开发预留 / Placeholder 面板 -->
          <div 
            v-if="['profile', 'snapshots', 'customization', 'hooks', 'connections', 'git', 'environment', 'worktree', 'browser', 'computer', 'archive'].includes(activeTab)"
            class="settings-panel-view"
          >
            <div class="draft-feature-card">
              <div class="draft-header">
                <div class="draft-badge">开发预留 / Draft Mode</div>
                <h3>该面板功能正在闭门设计中</h3>
              </div>
              <p class="draft-desc">
                我们正在针对本地工作区与 Agent 执行引擎进行极致打磨。本栏目作为 Codex 顶奢规范预留接口，在未来的版本中，它将用于装配并定制高级属性（例如内置浏览器隔离级别、Git 自动合并策略、或电脑的执行安全性级别）。
              </p>
              
              <!-- Aesthetic Disabled Controls Mockup to make it look alive but not fully functional -->
              <div class="mock-fields">
                <div class="mock-row disabled">
                  <span>启用自动分支回滚 (Auto Git-Rollback)</span>
                  <button class="switch-toggle" disabled><span class="switch-dot"></span></button>
                </div>
                <div class="mock-row disabled">
                  <span>内置浏览器无痕模式 (Sandbox Incognito)</span>
                  <button class="switch-toggle active" disabled><span class="switch-dot"></span></button>
                </div>
              </div>
            </div>
          </div>

        </div>
      </main>

    </div>
  </div>
</template>

<style scoped>
/* ── 最外层遮罩 ── */
.marketplace-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

/* ── 顶奢双栏模态大框 ── */
.settings-modal {
  width: 100%;
  max-width: 1080px;
  height: 90vh;
  max-height: 820px;
  background: rgba(var(--bg-panel-rgb, 10, 10, 10), 0.85);
  backdrop-filter: blur(36px);
  -webkit-backdrop-filter: blur(36px);
  border: 1px solid var(--border-strong);
  border-radius: 20px;
  color: var(--text-primary, #eee);
  box-shadow: 0 32px 80px rgba(0, 0, 0, 0.7), 0 0 0 1px rgba(255, 255, 255, 0.03);
  display: flex;
  flex-direction: row;
  overflow: hidden;
  animation: scaleUp 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes scaleUp {
  from { transform: scale(0.96); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

/* ── 🟢 左侧：顶奢导航栏 ── */
.settings-sidebar {
  width: 240px;
  background: rgba(5, 5, 5, 0.35);
  border-right: 1px solid var(--border-dim);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  padding: 24px 12px;
  overflow-y: auto;
}

/* Mac 点 */
.window-controls {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  padding-left: 12px;
}

.control-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  cursor: pointer;
  position: relative;
  display: inline-block;
}
.control-dot.close { background: #ef4444; }
.control-dot.minimize { background: #f59e0b; }
.control-dot.maximize { background: #10b981; }

.control-dot:hover::after {
  content: '✕';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: rgba(0,0,0,0.5);
  font-size: 8px;
  font-weight: bold;
}

/* 返回应用按钮 */
.back-to-app-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 10px 16px;
  margin-bottom: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.back-to-app-btn:hover {
  background: rgba(var(--accent-rgb, 124, 106, 247), 0.15);
  border-color: var(--accent);
  color: var(--accent);
  box-shadow: 0 0 12px var(--accent-glow);
}

.back-arrow-icon {
  transition: transform 0.2s ease;
}
.back-to-app-btn:hover .back-arrow-icon {
  transform: translateX(-3px);
}

.back-text {
  font-size: 12px;
  font-weight: 600;
}

/* 导航项 */
.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: var(--text-secondary, #999);
  padding: 10px 14px;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s ease;
  user-select: none;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-primary, #eee);
  padding-left: 18px;
}

.nav-item.active {
  background: rgba(var(--accent-rgb, 124, 106, 247), 0.1);
  color: var(--accent);
}

.active-bar {
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  background: var(--accent);
  border-radius: 0 3px 3px 0;
}

.nav-icon {
  flex-shrink: 0;
  opacity: 0.7;
}
.nav-item.active .nav-icon {
  opacity: 1;
}

.nav-label {
  font-size: 12px;
  font-weight: 500;
}

/* ── 🔵 右侧：主内容区 ── */
.settings-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: rgba(var(--bg-panel-rgb, 10, 10, 10), 0.25);
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 32px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.content-header h2 {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--text-primary);
}

.close-btn-right {
  background: transparent;
  border: none;
  color: var(--text-muted, #555);
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn-right:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.05);
}

.content-body {
  padding: 32px;
  flex: 1;
  overflow-y: auto;
}

/* 通用面板视图 */
.settings-panel-view {
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.view-description {
  font-size: 12.5px;
  color: var(--text-secondary, #999);
  margin-bottom: 24px;
}

/* ── 错误组件 ── */
.settings-error {
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.15);
  color: #f87171;
  padding: 12px 18px;
  border-radius: 8px;
  font-size: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  font-family: var(--font-mono, monospace);
}
.settings-error button {
  background: transparent;
  border: none;
  color: inherit;
  cursor: pointer;
}

/* ── 1. 常规配置行 ── */
.settings-group {
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-dim);
  border-radius: 12px;
  overflow: hidden;
}

.settings-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-dim);
}

.settings-row:last-child {
  border-bottom: none;
}

.row-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 70%;
}

.row-title {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-primary, #ddd);
}

.row-desc {
  font-size: 11.5px;
  color: var(--text-muted, #777);
  line-height: 1.5;
}

/* 常规高端表单元素 */
.premium-select {
  background: var(--bg-panel, #111);
  border: 1px solid var(--border-dim);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 12px;
  padding: 8px 12px;
  outline: none;
  cursor: pointer;
  transition: all 0.2s ease;
}
.premium-select:focus {
  border-color: var(--accent);
  box-shadow: 0 0 10px var(--accent-glow);
}

.premium-slider {
  -webkit-appearance: none;
  width: 150px;
  height: 4px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.1);
  outline: none;
}
.premium-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--accent);
  cursor: pointer;
  box-shadow: 0 0 8px var(--accent-glow);
  transition: transform 0.1s ease;
}
.premium-slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

/* ── 2. 主题配置格 ── */
.theme-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.theme-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(255, 255, 255, 0.02) !important;
  border: 1px solid var(--border-dim) !important;
  border-radius: 10px;
  padding: 12px 18px;
  cursor: pointer;
  color: var(--text-primary);
  text-align: left;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
}

.theme-card:hover {
  background: rgba(255, 255, 255, 0.04) !important;
  border-color: rgba(255, 255, 255, 0.12) !important;
  transform: translateY(-2px);
}

.theme-card.active {
  border-color: var(--accent) !important;
  background: rgba(var(--accent-rgb, 124, 106, 247), 0.1) !important;
  box-shadow: 0 0 16px var(--accent-glow);
}

.theme-card-preview {
  display: flex;
  gap: 4px;
  align-items: center;
}

.preview-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: inline-block;
}

.theme-card-name {
  font-size: 12.5px;
  font-weight: 500;
}

/* ── 3. AI 服务商及模型配置 ── */
.provider-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.provider-card {
  background: rgba(255, 255, 255, 0.02) !important;
  border: 1px solid var(--border-dim) !important;
  border-radius: 12px;
  overflow: hidden;
  transition: border-color 0.2s;
}
.provider-card:hover {
  border-color: rgba(255, 255, 255, 0.08);
}

.provider-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  cursor: pointer;
  user-select: none;
}

.prov-info {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
  flex: 1;
}

.prov-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #eee);
  flex-shrink: 0;
}

.prov-url {
  font-size: 11.5px;
  color: var(--text-muted, #666);
  font-family: var(--font-mono, monospace);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 320px;
}

.prov-key-hint {
  font-size: 10px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-muted, #555);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: var(--font-mono, monospace);
  flex-shrink: 0;
}

.prov-actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

.sync-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  color: var(--text-secondary, #aaa);
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}
.sync-btn:hover:not(:disabled) {
  color: var(--text-primary, #eee);
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.12);
}
.sync-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sync-icon {
  flex-shrink: 0;
}
.sync-icon.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.delete-icon-btn, .edit-icon-btn, .star-icon-btn {
  background: transparent;
  border: none;
  color: var(--text-muted, #555);
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.delete-icon-btn:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.08);
}
.edit-icon-btn:hover {
  color: var(--accent);
  background: rgba(var(--accent-rgb, 124, 106, 247), 0.08);
}
.star-icon-btn:hover, .star-icon-btn.active {
  color: #ffb800;
  background: rgba(255, 184, 0, 0.08);
}
.star-icon-btn.active .star-icon {
  fill: #ffb800;
}

.expand-chevron {
  color: var(--text-muted, #555);
  transition: transform 0.2s ease;
}
.expand-chevron.open {
  transform: rotate(180deg);
  color: var(--text-secondary);
}

/* 幽灵添加卡 */
.ghost-add-card {
  border: 1px dashed rgba(var(--accent-rgb, 124, 106, 247), 0.3) !important;
  background: rgba(var(--accent-rgb, 124, 106, 247), 0.02) !important;
  transition: all 0.25s ease !important;
}

.ghost-add-card:hover {
  border-color: var(--accent) !important;
  background: rgba(var(--accent-rgb, 124, 106, 247), 0.05) !important;
}

.ghost-card-trigger {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  cursor: pointer;
  color: var(--text-secondary);
  font-weight: 500;
  font-size: 12.5px;
}
.ghost-add-card:hover .ghost-card-trigger {
  color: var(--accent);
}

.ghost-icon {
  font-size: 14px;
}

.add-provider-inline-form, .edit-provider-form {
  padding: 20px 24px;
  border-top: 1px solid var(--border-dim);
  background: rgba(0, 0, 0, 0.1);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted, #666);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.form-group input {
  background: var(--bg-panel, #111) !important;
  border: 1px solid var(--border-dim) !important;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 12px;
  color: var(--text-primary, #eee);
  transition: all 0.2s ease;
}
.form-group input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 10px var(--accent-glow);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.save-btn {
  padding: 8px 18px;
  background: var(--accent);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s, transform 0.1s;
}
.save-btn:hover {
  opacity: 0.95;
}
.save-btn:active {
  transform: scale(0.97);
}

.cancel-btn {
  background: transparent;
  border: 1px solid var(--border-dim);
  color: var(--text-secondary);
  cursor: pointer;
  padding: 8px 18px;
  border-radius: 8px;
  font-size: 12px;
  transition: all 0.15s;
}
.cancel-btn:hover {
  border-color: var(--text-muted);
  color: var(--text-primary);
}

/* 模型的表格 */
.provider-models-wrapper {
  border-top: 1px solid var(--border-dim) !important;
  background: rgba(0, 0, 0, 0.15) !important;
  padding: 16px 24px;
}

.models-loading, .models-empty {
  font-size: 11.5px;
  color: var(--text-muted, #555);
  padding: 24px 0;
  text-align: center;
}

.models-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  text-align: left;
}

.models-table th {
  padding: 10px;
  color: var(--text-secondary);
  font-weight: 600;
  border-bottom: 1px solid var(--border-dim) !important;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.models-table td {
  padding: 12px 10px;
  border-bottom: 1px solid var(--border-dim) !important;
  color: var(--text-secondary, #bbb);
  vertical-align: middle;
}
.models-table tr.disabled td {
  opacity: 0.45;
}

.td-model-id {
  color: var(--text-primary, #ddd);
}

.model-name-input {
  width: 100%;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 12px;
  color: var(--text-primary, #ddd);
  transition: all 0.15s;
}
.model-name-input:hover {
  background: rgba(255, 255, 255, 0.03);
  border-color: rgba(255,255,255,0.06);
}
.model-name-input:focus {
  background: var(--bg-panel, #111) !important;
  border-color: var(--accent);
  outline: none;
}

.td-tags {
  display: flex;
  align-items: center;
  gap: 6px;
}

.cap-tag {
  font-size: 9.5px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.badge-thinking {
  background: rgba(var(--accent-rgb, 124, 106, 247), 0.1);
  color: var(--accent);
  border: 1px solid rgba(var(--accent-rgb, 124, 106, 247), 0.2);
}

.badge-tools {
  background: rgba(52, 211, 153, 0.08);
  color: #34d399;
  border: 1px solid rgba(52, 211, 153, 0.15);
}

/* ── 4. MCP 服务器配置面板 ── */
.mcp-servers-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 24px;
}

.mcp-server-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-dim);
  border-radius: 12px;
  padding: 18px 24px;
}

.card-header-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.server-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.server-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
}
.server-dot.active {
  background: #10b981;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
}

.server-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.server-type {
  font-size: 10px;
  background: rgba(255,255,255,0.05);
  color: var(--text-muted);
  padding: 2px 6px;
  border-radius: 4px;
}

.server-status.active {
  font-size: 11px;
  color: #10b981;
  font-weight: 600;
}

.server-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.server-detail-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
}

.detail-val {
  font-size: 12px;
  color: var(--text-secondary);
}

.tool-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.tool-badge {
  font-size: 10.5px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-dim);
  color: var(--text-secondary);
  padding: 3px 8px;
  border-radius: 6px;
  font-family: var(--font-mono, monospace);
}

/* MCP 控制台 */
.mcp-terminal-section {
  border: 1px solid var(--border-dim);
  border-radius: 12px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.2);
}

.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  cursor: pointer;
  user-select: none;
  background: rgba(255, 255, 255, 0.02);
}

.term-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  font-weight: 600;
}

.terminal-icon {
  color: var(--accent);
  font-weight: 800;
}

.chevron {
  font-size: 9px;
  color: var(--text-muted);
  transition: transform 0.2s ease;
}
.chevron.open {
  transform: rotate(180deg);
}

.terminal-body {
  padding: 16px 20px;
  background: rgba(0, 0, 0, 0.4);
  font-size: 11.5px;
  line-height: 1.6;
  max-height: 150px;
  overflow-y: auto;
  border-top: 1px solid var(--border-dim);
}

.log-line {
  color: #a1a1aa;
}
.log-line.success {
  color: #34d399;
}

/* ── 5. 键盘快捷键面板 ── */
.shortcuts-table {
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-dim);
  border-radius: 12px;
  overflow: hidden;
}

.shortcut-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-dim);
}
.shortcut-item:last-child {
  border-bottom: none;
}

.shortcut-name {
  font-size: 12.5px;
  color: var(--text-secondary);
}

.shortcut-keys kbd {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid var(--border-dim);
  border-radius: 4px;
  color: var(--text-primary);
  font-size: 11px;
  padding: 3px 6px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.5);
  font-family: var(--font-mono, monospace);
}

/* ── 6. 使用与计费面板 ── */
.billing-dash {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.billing-card-mini {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-dim);
  border-radius: 12px;
  padding: 18px 24px;
}

.mini-title {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 8px;
}

.mini-value {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 6px;
}
.mini-value.highlight-cyan {
  color: #22d3ee;
  text-shadow: 0 0 12px rgba(34, 211, 238, 0.3);
}
.mini-value.text-accent {
  color: var(--accent);
  text-shadow: 0 0 12px var(--accent-glow);
}

.mini-subtitle {
  font-size: 10.5px;
  color: var(--text-muted);
}

.progress-section {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-dim);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 24px;
}

.progress-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12.5px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.progress-track {
  height: 6px;
  border-radius: 3px;
  background: rgba(255,255,255,0.06);
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 3px;
  background: linear-gradient(90deg, var(--accent) 0%, #22d3ee 100%);
  box-shadow: 0 0 8px rgba(34, 211, 238, 0.4);
}

.chart-section {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-dim);
  border-radius: 12px;
  padding: 20px 24px;
}

.chart-header {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 20px;
}

.bar-chart-container {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  height: 120px;
  padding: 0 10px;
}

.bar-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  width: 40px;
}

.bar-fill {
  width: 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 6px 6px 0 0;
  transition: all 0.3s ease;
  cursor: pointer;
}
.bar-fill:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: scaleY(1.05);
}

.bar-fill.active {
  background: linear-gradient(180deg, var(--accent) 0%, rgba(var(--accent-rgb, 124, 106, 247), 0.3) 100%);
  box-shadow: 0 0 12px var(--accent-glow);
}

.bar-label {
  font-size: 10.5px;
  color: var(--text-muted);
}
.bar-col.active .bar-label {
  color: var(--accent);
  font-weight: 600;
}

/* ── 7. 开发预留 / Draft Mode ── */
.draft-feature-card {
  background: rgba(255, 255, 255, 0.01);
  border: 1px dashed rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  padding: 28px;
  text-align: left;
}

.draft-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.draft-badge {
  font-size: 9.5px;
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.2);
  padding: 2px 8px;
  border-radius: 4px;
  width: fit-content;
  font-weight: 600;
}

.draft-header h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.draft-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 24px;
}

.mock-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mock-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-dim);
  border-radius: 8px;
}

.mock-row.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.mock-row span {
  font-size: 12px;
  color: var(--text-secondary);
}

/* ── 开关 (Switch) ── */
.switch-toggle {
  width: 32px;
  height: 18px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.08);
  border: none;
  cursor: pointer;
  position: relative;
  transition: background 0.2s;
  display: inline-flex;
  align-items: center;
  padding: 0 2px;
}
.switch-toggle:disabled {
  cursor: not-allowed;
}
.switch-toggle.active {
  background: var(--accent);
}

.switch-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
  transition: transform 0.2s cubic-bezier(0.2, 0.9, 0.3, 1);
}
.switch-toggle.active .switch-dot {
  transform: translateX(14px);
}

/* ── 动画过渡 ── */
.expand-enter-active,
.expand-leave-active {
  transition: max-height 0.25s ease-out, opacity 0.2s ease, padding 0.25s ease;
  overflow: hidden;
  max-height: 600px;
}
.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}

.mono-text {
  font-family: var(--font-mono, monospace);
  font-size: 11px;
}
</style>
