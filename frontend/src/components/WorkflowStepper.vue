<template>
  <div class="wf">
    <div class="wf-track">
      <div
        v-for="(s, idx) in steps"
        :key="s.id"
        class="wf-step"
        :class="{
          done: s.done,
          active: s.active,
          locked: !s.available,
        }"
      >
        <component
          :is="s.available ? 'router-link' : 'span'"
          class="wf-link"
          :to="s.available ? s.to : undefined"
          :aria-disabled="s.available ? undefined : 'true'"
          @click.prevent="onClickLocked(s)"
        >
          <span class="wf-num">{{ idx + 1 }}</span>
          <span class="wf-label">{{ s.label }}</span>
          <span v-if="s.done" class="wf-badge">已完成</span>
          <span v-else-if="s.active" class="wf-badge wf-badge-active">当前</span>
          <span v-else-if="!s.available" class="wf-badge wf-badge-locked">未就绪</span>
        </component>
        <div v-if="!s.available && s.reason" class="wf-reason">{{ s.reason }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useDataStore } from '../stores/dataStore'
import { useModelStore } from '../stores/modelStore'
import { useStatsStore } from '../stores/statsStore'
import { useNoticeStore } from '../stores/noticeStore'
import { pushWarningNotice } from '../utils/uiFeedback'

const route = useRoute()
const dataStore = useDataStore()
const modelStore = useModelStore()
const statsStore = useStatsStore()
const noticeStore = useNoticeStore()

function normalizeSyntax(s) {
  return String(s || '')
    .split('\n')
    .map((row) => row.trim())
    .filter(Boolean)
    .join('\n')
}

const currentSyntaxNorm = computed(() => normalizeSyntax(modelStore.lavaanSyntax))
const isFitStale = computed(() => {
  if (!statsStore.fitIndices) return false
  const current = currentSyntaxNorm.value
  const last = String(statsStore.lastFitSyntaxNorm || '')
  if (!last) return false
  return current !== last
})

const steps = computed(() => {
  const hasData = Boolean(dataStore.dataKey)
  const hasSyntax = Boolean(modelStore.lavaanSyntax)
  const hasFit = Boolean(statsStore.fitIndices)

  const list = [
    {
      id: 'upload',
      label: '上传数据',
      to: { path: '/data' },
      available: true,
      done: hasData,
      reason: '',
    },
    {
      id: 'model',
      label: '建模',
      to: { path: '/model' },
      available: hasData,
      done: false,
      reason: hasData ? '' : '请先上传数据（获得 data_key）',
    },
    {
      id: 'syntax',
      label: '生成语法',
      to: { path: '/model', query: { focus: 'syntax' } },
      available: hasData,
      done: hasSyntax,
      reason: hasData ? '请在建模页点击“生成 lavaan 语法”' : '请先上传数据（获得 data_key）',
    },
    {
      id: 'fit',
      label: '估算',
      to: { path: '/results' },
      available: hasData && hasSyntax,
      done: hasFit && !isFitStale.value,
      reason: !hasData
        ? '请先上传数据（获得 data_key）'
        : !hasSyntax
          ? '请先在建模页生成 lavaan 语法'
          : '请在结果页点击“运行估算”',
    },
    {
      id: 'export',
      label: '导出',
      to: { path: '/results' },
      available: hasData && hasSyntax && hasFit && !isFitStale.value,
      done: false,
      reason: !hasData
        ? '请先上传数据（获得 data_key）'
        : !hasSyntax
          ? '请先在建模页生成 lavaan 语法'
          : !hasFit
            ? '请先在结果页运行一次估算'
            : '检测到语法已修改：请先重新估算（避免导出误导性结果）',
    },
  ]

  const path = route.path
  for (const s of list) {
    s.active = (s.id === 'upload' && path === '/data') ||
      ((s.id === 'model' || s.id === 'syntax') && path === '/model') ||
      ((s.id === 'fit' || s.id === 'export') && path === '/results')
  }
  return list
})

function onClickLocked(step) {
  if (!step || step.available) return
  if (step.reason) pushWarningNotice(noticeStore, step.reason, '流程未就绪')
}
</script>

<style scoped>
.wf {
  padding: 0.55rem 1.5rem 0.75rem;
  border-top: 1px solid var(--border-light);
}

.wf-track {
  max-width: 1400px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.6rem;
}

.wf-step {
  min-width: 0;
}

.wf-link {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.55rem 0.6rem;
  border: 1px solid var(--border-light);
  background: var(--bg-paper);
  text-decoration: none;
  color: var(--text-secondary);
  transition: border-color var(--transition-fast), background var(--transition-fast);
}

.wf-link:hover {
  border-color: var(--accent-cta);
  background: var(--accent-cta-subtle);
}

.wf-num {
  width: 18px;
  height: 18px;
  border-radius: 999px;
  border: 1px solid var(--border-light);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  color: var(--text-muted);
  flex-shrink: 0;
}

.wf-label {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.wf-badge {
  margin-left: auto;
  font-size: 0.72rem;
  color: var(--text-muted);
  border: 1px solid var(--border-light);
  padding: 0.18rem 0.4rem;
  border-radius: 999px;
  flex-shrink: 0;
}

.wf-badge-active {
  color: var(--accent-cta);
  border-color: rgba(30, 127, 255, 0.35);
  background: rgba(30, 127, 255, 0.06);
}

.wf-badge-locked {
  color: #8b6b00;
  border-color: rgba(139, 107, 0, 0.35);
  background: rgba(139, 107, 0, 0.08);
}

.wf-step.done .wf-num {
  border-color: rgba(15, 122, 66, 0.35);
  background: rgba(15, 122, 66, 0.06);
  color: #0f7a42;
}

.wf-step.done .wf-badge {
  color: #0f7a42;
  border-color: rgba(15, 122, 66, 0.35);
  background: rgba(15, 122, 66, 0.06);
}

.wf-step.locked .wf-link {
  cursor: not-allowed;
  opacity: 0.86;
}

.wf-step.locked .wf-link:hover {
  border-color: var(--border-light);
  background: var(--bg-paper);
}

.wf-reason {
  margin-top: 0.3rem;
  font-size: 0.75rem;
  color: var(--text-muted);
  line-height: 1.25;
}

@media (max-width: 900px) {
  .wf-track {
    grid-template-columns: 1fr;
  }
  .wf-link {
    justify-content: space-between;
  }
}
</style>

