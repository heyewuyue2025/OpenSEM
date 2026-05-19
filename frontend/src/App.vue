<template>
  <div class="app">
    <!-- Primary Header -->
    <header v-if="!isHomeRoute" class="header">
      <div class="header-accent"></div>
      <div class="header-inner">
        <div class="menu-wrap" ref="menuWrapEl">
          <button
            class="menu-btn"
            aria-label="讲解目录"
            aria-haspopup="true"
            :aria-expanded="showGuideMenu ? 'true' : 'false'"
            @click="toggleGuideMenu"
          >
            <span></span><span></span><span></span>
          </button>
          <div v-if="showGuideMenu" class="menu-panel" role="menu" aria-label="首页讲解目录">
            <router-link to="/home/product-position" class="menu-item" role="menuitem" @click="closeGuideMenu">
              产品定位
            </router-link>
            <router-link to="/home/core-value" class="menu-item" role="menuitem" @click="closeGuideMenu">
              核心价值
            </router-link>
            <router-link to="/home/analysis-flow" class="menu-item" role="menuitem" @click="closeGuideMenu">
              分析流程
            </router-link>
            <router-link to="/home/trust-export" class="menu-item" role="menuitem" @click="closeGuideMenu">
              可信与导出
            </router-link>
          </div>
        </div>
        <div class="brand">
          <h1 class="masthead">OpenSEM</h1>
          <p class="slogan">Structural Equation Modeling · 结构方程建模</p>
        </div>
        <div class="header-actions">
          <button class="btn-ghost" @click="resetAnalysis">重置 / Reset</button>
          <router-link to="/data" class="btn-cta">新建分析 / New</router-link>
        </div>
      </div>
    </header>
    <!-- Secondary Nav + Status Bar -->
    <div v-if="!isHomeRoute" class="sub-header">
      <nav class="sub-nav">
        <template v-for="(item, idx) in mainNavItems" :key="item.to">
          <router-link :to="item.to">{{ item.label }}</router-link>
          <span v-if="idx < mainNavItems.length - 1" class="nav-divider"></span>
        </template>
      </nav>
      <p v-if="sessionNotice" class="session-notice">{{ sessionNotice }}</p>
    </div>
    <main :class="['main', { 'main--home': isHomeRoute }]">
      <router-view v-slot="{ Component }">
        <transition name="page-cinematic-hero" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    <footer v-if="!isHomeRoute" class="footer">
      <span class="footer-dot"></span>
      <span>数据已加密传输，计算完成后自动销毁 · Data encrypted, auto-destroyed after computation</span>
    </footer>
    <div
      v-if="noticeStore.current"
      :class="[NOTICE.base, resolveNoticeTone(noticeStore.current.type)]"
      role="status"
      aria-live="polite"
    >
      <div :class="NOTICE.title">{{ noticeStore.current.title || '系统提示' }}</div>
      <div :class="NOTICE.message">{{ noticeStore.current.message }}</div>
      <button :class="NOTICE.close" @click="noticeStore.dismiss">关闭</button>
    </div>
    <div v-if="dialogStore.current" :class="DIALOG.mask" role="dialog" aria-modal="true">
      <div :class="DIALOG.panel">
        <div :class="DIALOG.title">{{ dialogStore.current.title || '请确认' }}</div>
        <div :class="DIALOG.message">{{ dialogStore.current.message }}</div>
        <div :class="DIALOG.actions">
          <button :class="DIALOG.cancel" @click="dialogStore.cancel">
            {{ dialogStore.current.cancelText || '取消' }}
          </button>
          <button :class="DIALOG.confirm" @click="dialogStore.accept">
            {{ dialogStore.current.confirmText || '继续' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useDataStore } from './stores/dataStore'
import { useModelStore } from './stores/modelStore'
import { useStatsStore } from './stores/statsStore'
import { useNoticeStore } from './stores/noticeStore'
import { useDialogStore } from './stores/dialogStore'
import { NOTICE, resolveNoticeTone } from './ui/noticeContract'
import { DIALOG } from './ui/dialogContract'
import { resolveMainNavItems } from './ui/navContract'
import { requestUserConfirm } from './utils/uiFeedback'

const dataStore = useDataStore()
const modelStore = useModelStore()
const statsStore = useStatsStore()
const noticeStore = useNoticeStore()
const dialogStore = useDialogStore()
const sessionNotice = ref('')
const mainNavItems = resolveMainNavItems()
const route = useRoute()
const isHomeRoute = computed(() => route.path === '/')
const showGuideMenu = ref(false)
const menuWrapEl = ref(null)

async function resetAnalysis() {
  const ok = await requestUserConfirm(dialogStore, {
    title: '确认重置',
    message: '将清空当前上传数据、模型语法与估算结果，是否继续？',
    confirmText: '确认重置',
    cancelText: '取消',
  })
  if (!ok) return
  dataStore.clearData()
  modelStore.clearModelResult()
  statsStore.clearAllResults()
  // 同时清理“MI 忽略列表”（按语法版本号分桶存储，直接清空所有以避免跨项目污染）
  try {
    const keys = Object.keys(localStorage)
    for (const k of keys) {
      if (k.startsWith('opensem:mi:ignored:v1:') || k.startsWith('OpenSEM:mi:ignored:v1:')) {
        localStorage.removeItem(k)
      }
    }
  } catch (_) {
    // ignore localStorage access errors
  }
}

function toggleGuideMenu() {
  showGuideMenu.value = !showGuideMenu.value
}

function closeGuideMenu() {
  showGuideMenu.value = false
}

function handleDocumentPointerDown(event) {
  if (!showGuideMenu.value) return
  const wrap = menuWrapEl.value
  if (wrap && event.target instanceof Node && !wrap.contains(event.target)) {
    closeGuideMenu()
  }
}

onMounted(async () => {
  document.addEventListener('pointerdown', handleDocumentPointerDown)
  const result = await dataStore.validatePersistedDataKey()
  if (!result.valid) {
    modelStore.clearModelResult()
    statsStore.clearFitResult()
    sessionNotice.value = dataStore.sessionInvalidWarning
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleDocumentPointerDown)
})
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  position: relative;
  z-index: 80;
  background: linear-gradient(180deg, rgba(7, 13, 26, 0.96), rgba(7, 13, 26, 0.88));
  color: var(--text-primary);
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(12px);
}

.header-accent {
  position: absolute;
  left: 0.9rem;
  right: 0.9rem;
  bottom: 0;
  height: 2px;
  background: linear-gradient(90deg, rgba(139, 200, 255, 0), rgba(139, 200, 255, 0.95), rgba(239, 184, 120, 0));
}

.header-inner {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: clamp(0.66rem, 1.2vw, 0.86rem) var(--osem-app-chrome-pad-x);
  max-width: 1400px;
  margin: 0 auto;
}

.menu-btn {
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: none;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  color: inherit;
  cursor: pointer;
  padding: 0.5rem;
  min-height: 40px;
  justify-content: center;
}
.menu-wrap {
  position: relative;
  z-index: 95;
}
.menu-btn span {
  display: block;
  width: 16px;
  height: 2px;
  background: currentColor;
  transition: var(--transition-fast);
}

.menu-btn:hover {
  border-color: rgba(139, 200, 255, 0.62);
  color: #d8eeff;
}

.menu-panel {
  position: absolute;
  top: calc(100% + 0.45rem);
  left: 0;
  min-width: 182px;
  padding: 0.4rem;
  border: 1px solid var(--line-strong, var(--border));
  border-radius: var(--radius-md);
  background: linear-gradient(165deg, rgba(8, 16, 31, 0.98), rgba(6, 12, 23, 0.99));
  box-shadow: var(--shadow-glow, 0 16px 32px rgba(0, 0, 0, 0.36));
  backdrop-filter: blur(10px);
  z-index: 120;
}

.menu-item {
  display: block;
  padding: 0.5rem 0.62rem;
  border-radius: 0.52rem;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.82rem;
  font-weight: 600;
  line-height: 1.35;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.menu-item:hover {
  background: rgba(139, 200, 255, 0.14);
  color: #e8f4ff;
}

.brand {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.15rem;
  width: fit-content;
  max-width: min(62vw, 700px);
}

.masthead {
  font-family: var(--font-display);
  font-size: clamp(1.18rem, 1.9vw, 1.45rem);
  font-weight: 700;
  letter-spacing: 0.04em;
  line-height: 1.15;
  background: linear-gradient(90deg, #bff8ff, #86dfff 58%, #a6b8ff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.slogan {
  font-family: var(--font-ui);
  font-size: clamp(0.62rem, 0.95vw, 0.72rem);
  opacity: 0.78;
  color: var(--text-muted);
  margin-top: 0.1rem;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.icon-btn {
  background: none;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0.45rem;
  min-height: 40px;
  min-width: 40px;
  font-size: 0.95rem;
  transition: color var(--transition-fast);
}
.icon-btn:hover {
  color: #d9eeff;
  border-color: rgba(139, 200, 255, 0.62);
  background: rgba(139, 200, 255, 0.14);
}

.btn-cta {
  font-family: var(--font-ui);
  font-size: clamp(0.75rem, 1vw, 0.84rem);
  font-weight: 600;
  padding: 0.55rem 0.95rem;
  background: linear-gradient(140deg, #f0c38c, #eca25f);
  color: #142341;
  text-decoration: none;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  transition: background var(--transition-fast), box-shadow var(--transition-fast);
}
.btn-cta:hover {
  box-shadow: 0 12px 24px rgba(239, 167, 96, 0.3);
  transform: translateY(-1px);
}

.btn-ghost {
  font-family: var(--font-ui);
  font-size: clamp(0.72rem, 1vw, 0.82rem);
  font-weight: 600;
  padding: 0.48rem 0.8rem;
  background: rgba(10, 18, 33, 0.82);
  color: var(--text-secondary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  cursor: pointer;
  min-height: 40px;
}

.btn-ghost:hover {
  color: #d9eeff;
  border-color: rgba(139, 200, 255, 0.6);
  background: rgba(139, 200, 255, 0.14);
}

.sub-header {
  position: relative;
  z-index: 40;
  border-bottom: 1px solid var(--border-light);
  background: linear-gradient(180deg, rgba(7, 13, 26, 0.92), rgba(7, 13, 26, 0.82));
  backdrop-filter: blur(8px);
}

.session-notice {
  margin: 0;
  padding: 0.45rem var(--osem-app-chrome-pad-x) 0.55rem;
  font-size: var(--type-caption);
  color: var(--error);
  border-top: 1px solid var(--border-light);
}

.sub-nav {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 0;
  padding: 0.5rem var(--osem-app-chrome-pad-x);
  max-width: 1400px;
  margin: 0 auto;
}

.sub-nav a {
  position: relative;
  font-family: var(--font-ui);
  font-size: clamp(0.72rem, 0.9vw, 0.8rem);
  font-weight: 600;
  color: var(--text-secondary);
  text-decoration: none;
  padding: 0.32rem 0.75rem;
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  border-radius: 0;
  transition: color var(--transition-fast), background var(--transition-fast);
}

.sub-nav a::after {
  content: '';
  position: absolute;
  left: 0.75rem;
  right: 0.75rem;
  bottom: 0.2rem;
  height: 2px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(139, 200, 255, 0.9), rgba(239, 184, 120, 0.9));
  transform: scaleX(0);
  transform-origin: center;
  transition: transform 220ms cubic-bezier(0.22, 1, 0.36, 1);
}
.sub-nav a:hover {
  color: #e4f1ff;
  background: rgba(139, 200, 255, 0.16);
}
.sub-nav a:hover::after {
  transform: scaleX(0.7);
}
.sub-nav a.router-link-active {
  color: #f1f7ff;
  background: rgba(139, 200, 255, 0.18);
  box-shadow: inset 0 0 0 1px rgba(139, 200, 255, 0.44);
}
.sub-nav a.router-link-active::after {
  transform: scaleX(1);
}

.nav-divider {
  width: 1px;
  height: 12px;
  background: var(--border-light);
}

.main {
  flex: 1;
  padding: 0;
  max-width: 1320px;
  margin: 0 auto;
  width: 100%;
}

.main--home {
  max-width: none;
  margin: 0;
}

.footer {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: clamp(0.6rem, 1.5vw, 0.85rem) var(--osem-app-chrome-pad-x);
  background: rgba(7, 13, 26, 0.86);
  border-top: 1px solid var(--border-light);
  color: var(--text-secondary);
  font-family: var(--font-ui);
  font-size: clamp(0.7rem, 0.9vw, 0.78rem);
}

.footer-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent);
  flex-shrink: 0;
}

.page-soft-enter-active,
.page-soft-leave-active {
  transition: opacity 220ms cubic-bezier(0.22, 1, 0.36, 1), transform 220ms cubic-bezier(0.22, 1, 0.36, 1);
}
.page-soft-enter-from { opacity: 0; transform: translateY(6px) scale(0.995); }
.page-soft-leave-to { opacity: 0; transform: translateY(-3px) scale(0.998); }

.page-cinematic-enter-active,
.page-cinematic-leave-active {
  transition:
    opacity 420ms cubic-bezier(0.16, 1, 0.3, 1),
    transform 520ms cubic-bezier(0.16, 1, 0.3, 1),
    filter 420ms ease,
    clip-path 480ms cubic-bezier(0.16, 1, 0.3, 1);
  transform-origin: 50% 46%;
}
.page-cinematic-enter-from {
  opacity: 0;
  transform: translateY(24px) scale(0.984);
  filter: blur(10px) saturate(0.88) brightness(0.76);
  clip-path: inset(4% 1.5% 10% 1.5% round 20px);
}
.page-cinematic-leave-to {
  opacity: 0;
  transform: translateY(-16px) scale(1.01);
  filter: blur(8px) saturate(0.94) brightness(0.82);
  clip-path: inset(8% 2% 5% 2% round 18px);
}

.page-cinematic-hero-enter-active,
.page-cinematic-hero-leave-active {
  transition:
    opacity 560ms cubic-bezier(0.16, 1, 0.3, 1),
    transform 720ms cubic-bezier(0.16, 1, 0.3, 1),
    filter 580ms ease,
    clip-path 620ms cubic-bezier(0.16, 1, 0.3, 1);
  transform-origin: 50% 50%;
}

.page-cinematic-hero-enter-from {
  opacity: 0;
  transform: translateY(42px) scale(0.97);
  filter: blur(16px) saturate(0.82) brightness(0.72) contrast(0.9);
  clip-path: inset(10% 5% 14% 5% round 28px);
}

.page-cinematic-hero-leave-to {
  opacity: 0;
  transform: translateY(-28px) scale(1.03);
  filter: blur(14px) saturate(0.86) brightness(0.76) contrast(0.92);
  clip-path: inset(14% 6% 9% 6% round 24px);
}

.page-slide-enter-active,
.page-slide-leave-active {
  transition: opacity 230ms ease, transform 280ms cubic-bezier(0.22, 1, 0.36, 1);
}
.page-slide-enter-from { opacity: 0; transform: translateX(26px); }
.page-slide-leave-to { opacity: 0; transform: translateX(-18px); }

@media (max-width: 768px) {
  .slogan { display: none; }
  .brand {
    position: static;
    transform: none;
    margin-left: 0.5rem;
    align-items: flex-start;
  }
  .header-inner {
    gap: 0.6rem;
  }
  .header-actions {
    margin-left: auto;
    gap: 0.45rem;
  }
  .sub-nav { flex-wrap: wrap; justify-content: flex-start; }
  .menu-panel {
    left: 0;
    min-width: min(220px, calc(100vw - 1.6rem));
  }
}

@media (prefers-reduced-motion: reduce) {
  .page-soft-enter-active,
  .page-soft-leave-active,
  .page-cinematic-enter-active,
  .page-cinematic-leave-active,
  .page-cinematic-hero-enter-active,
  .page-cinematic-hero-leave-active,
  .page-slide-enter-active,
  .page-slide-leave-active {
    transition: none !important;
  }
}
</style>
