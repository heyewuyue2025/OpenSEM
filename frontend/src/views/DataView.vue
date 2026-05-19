<template>
  <div class="data-view osem-core-page" :style="corePageStyle">
    <div class="view-layout">
      <main class="main-col">
        <section class="section reveal" :style="{ transitionDelay: '0ms' }">
          <h3 class="section-label">DATA IMPORT / 数据导入</h3>
          <div class="section-rule"></div>
          <p class="parse-msg osem-core-intro">
            上传后会自动生成会话键 <TermTip ns="data" term="data_key" />，后续建模与估算将复用该键。
          </p>
          <div
            class="upload-card"
            :class="{ loading: dataStore.loading }"
            role="button"
            tabindex="0"
            @click="!dataStore.loading && triggerUpload()"
            @keydown.enter.prevent="!dataStore.loading && triggerUpload()"
            @keydown.space.prevent="!dataStore.loading && triggerUpload()"
          >
            <input ref="fileInput" type="file" accept=".csv,.xlsx,.sav" @change="onFileSelect" />
            <div v-if="dataStore.loading" class="upload-loading">
              <span class="spinner"></span>
              <p>解析中…</p>
            </div>
            <template v-else>
              <div class="upload-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              <p class="upload-text">拖拽或点击上传 · Drag or click to upload</p>
              <p class="upload-hint">CSV · XLSX · SAV · ≤ 100 MB</p>
            </template>
          </div>
          <div
            v-if="uploadFeedback"
            :class="[FEEDBACK.base, resolveFeedbackTone(uploadFeedback.kind), 'upload-feedback']"
          >
            <p :class="FEEDBACK.text">{{ uploadFeedback.text }}</p>
            <p :class="FEEDBACK.detail">{{ uploadFeedback.detail }}</p>
          </div>
        </section>

        <section class="section reveal" :style="{ transitionDelay: '120ms' }">
          <h3 class="section-label">VARIABLE PREVIEW / 变量预览</h3>
          <div class="section-rule"></div>
          <div v-if="dataStore.variables.length" class="variable-pool">
            <p class="pool-summary">
              有效样本 N = {{ dataStore.nRows }} · 共 {{ dataStore.nCols }} 个变量
            </p>
            <input
              v-model="searchVar"
              type="text"
              placeholder="搜索变量名 · Search"
              :class="[INP.input, 'var-search']"
            />
            <ul class="var-list">
              <li
                v-for="v in filteredVars"
                :key="v.name"
                class="var-item"
                :class="{ 'high-missing': v.missing_rate > 5 }"
              >
                <span class="var-name">{{ v.name }}</span>
                <span class="var-meta">
                  <span class="type-override">
                    <select
                      :class="[INP.selectCompact, 'type-select']"
                      :value="v.user_type || v.type"
                      @change="onTypeChange(v.name, $event.target.value)"
                    >
                      <option value="continuous">continuous / 连续</option>
                      <option value="ordinal">ordinal / 有序</option>
                    </select>
                  </span>
                  · N={{ v.n_valid }}
                  <span v-if="v.missing_rate > 0" class="missing"> 缺失 {{ v.missing_rate }}%</span>
                </span>
              </li>
            </ul>
            <p v-if="filteredVars.length === 0" class="no-match">无匹配变量</p>
          </div>
          <div v-else class="placeholder-box">
            <div :class="[FEEDBACK.base, resolveFeedbackTone('empty')]">
              <p :class="FEEDBACK.text">暂无变量预览</p>
              <p :class="FEEDBACK.detail">导入数据后将显示变量池，可继续变量类型确认与缺失检查。</p>
            </div>
          </div>
        </section>
      </main>
      <aside class="sidebar">
        <section class="sidebar-section osem-surface reveal" :style="{ transitionDelay: '80ms' }">
          <h3 class="sidebar-label">SUPPORTED FORMATS</h3>
          <ul class="format-list">
            <li><span class="ext">.csv</span> UTF-8 / GBK</li>
            <li><span class="ext">.xlsx</span> Excel</li>
            <li><span class="ext">.sav</span> SPSS</li>
          </ul>
        </section>
        <section class="sidebar-section osem-surface reveal" :style="{ transitionDelay: '160ms' }">
          <h3 class="sidebar-label">TIPS</h3>
          <p class="sidebar-tip">缺失率 &gt; 5% 将触发处理提示 <TermTip ns="data" term="missing_strategy" /></p>
          <p class="sidebar-tip">
            上传后数据会缓存到本机临时目录（可用 <code>OPENSEM_DATA_STORE_DIR</code> 配置目录）以避免后端重启丢失；
            若启用 Redis，会额外写入 Redis 供 worker 共享（可能有 TTL，例如 1h）。
          </p>
        </section>
      </aside>
    </div>

    <!-- 缺失率 > 5% 预警弹窗 PRD: 强制用户选择处理方案后方可继续 -->
    <div v-if="showMissingModal" class="modal-overlay" @click.self="onMissingOverlayClick">
      <div class="modal">
        <h4>缺失率预警</h4>
        <p>检测到部分变量缺失率超过 5%。根据 PRD，你需要先选择一种处理方案，才可以继续建模与估算。</p>

        <div class="missing-options">
          <label class="opt">
            <input type="radio" value="listwise" v-model="selectedMissingStrategy" />
            <span class="opt-title">列表删除（Listwise deletion）</span>
            <span class="opt-desc">删除含任意缺失值的样本行（Phase 1 默认）</span>
          </label>
          <label class="opt">
            <input type="radio" value="fiml" v-model="selectedMissingStrategy" />
            <span class="opt-title">FIML（Full Information ML）</span>
            <span class="opt-desc">使用缺失信息的极大似然（更接近学术实践；计算可能更慢）</span>
          </label>
          <label class="opt">
            <input type="radio" value="mean_impute" v-model="selectedMissingStrategy" />
            <span class="opt-title">均值插补（Mean imputation）</span>
            <span class="opt-desc">仅对数值列缺失值用列均值填补（谨慎使用）</span>
          </label>
        </div>

        <p class="modal-hint">
          提示：选择会被保存；估算完成后会显示“处理后有效 N”。
        </p>

        <button
          type="button"
          :class="[BTN.primary, 'data-missing-confirm']"
          :disabled="!selectedMissingStrategy"
          @click="confirmMissingStrategy"
        >
          确认并继续
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useDataStore } from '../stores/dataStore'
import TermTip from '../components/TermTip.vue'
import { resolveUploadFeedback } from './data/uploadFeedback'
import { BTN } from '../ui/buttonContract.js'
import { INP } from '../ui/inputContract.js'
import { FEEDBACK, resolveFeedbackTone } from '../ui/feedbackContract.js'
import { useOsemCorePageStyle } from './core/useOsemCorePageStyle'

const dataStore = useDataStore()
const fileInput = ref(null)
const searchVar = ref('')
const showMissingModal = ref(false)
const selectedMissingStrategy = ref('')
const { corePageStyle } = useOsemCorePageStyle('data')

const filteredVars = computed(() => {
  const q = searchVar.value.trim().toLowerCase()
  if (!q) return dataStore.variables
  return dataStore.variables.filter((v) => v.name.toLowerCase().includes(q))
})

const uploadFeedback = computed(() =>
  resolveUploadFeedback({
    loading: dataStore.loading,
    error: dataStore.error,
    sessionInvalidWarning: dataStore.sessionInvalidWarning,
    parseMessage: dataStore.parseMessage,
  })
)

function onTypeChange(name, nextType) {
  dataStore.setVariableType(name, nextType)
}

function triggerUpload() {
  fileInput.value?.click()
}

async function onFileSelect(e) {
  const f = e.target.files?.[0]
  if (!f) return
  try {
    await dataStore.parseFile(f)
    if (dataStore.highMissingWarning) {
      selectedMissingStrategy.value = dataStore.missingStrategy || ''
      showMissingModal.value = true
    }
  } catch (_) {
    // error shown in template
  }
  e.target.value = ''
}

function needsMissingStrategy() {
  return Boolean(dataStore.highMissingWarning && !dataStore.missingStrategy)
}

function confirmMissingStrategy() {
  if (!selectedMissingStrategy.value) return
  dataStore.setMissingStrategy(selectedMissingStrategy.value)
  showMissingModal.value = false
}

function onMissingOverlayClick() {
  // 强制选择：如果需要选择，则不允许点击遮罩关闭
  if (needsMissingStrategy()) return
  showMissingModal.value = false
}

watch(
  () => dataStore.highMissingWarning,
  (v) => {
    if (v && !dataStore.missingStrategy) {
      selectedMissingStrategy.value = ''
      showMissingModal.value = true
    }
  }
)

onMounted(() => {
  document.querySelector('.data-view')?.classList.add('visible')
  dataStore.validatePersistedDataKey()
})
</script>

<style scoped>
.data-view {
  --osem-core-bg-nebula-a: rgba(108, 176, 255, 0.21);
  --osem-core-bg-nebula-b: rgba(239, 170, 117, 0.14);
  --osem-core-bg-nebula-c: rgba(99, 151, 236, 0.14);
  padding: var(--osem-core-outer-pad, clamp(1.5rem, 3vw, 2.5rem));
  position: relative;
}

.view-layout {
  display: grid;
  grid-template-columns: 1fr 260px;
  gap: clamp(1.5rem, 3vw, 2rem);
  align-items: start;
}

.section-label, .sidebar-label {
  margin-bottom: 0.5rem;
}

.section-rule {
  height: 1px;
  background: var(--line-soft);
  margin-bottom: 1rem;
}

.upload-card {
  position: relative;
  border: 1px dashed rgba(145, 183, 245, 0.5);
  border-radius: var(--radius-md);
  padding: clamp(2rem, 4vw, 3rem);
  text-align: center;
  background: linear-gradient(155deg, rgba(11, 20, 37, 0.88), rgba(8, 15, 27, 0.9));
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: border-color var(--transition-fast), background var(--transition-fast), box-shadow var(--transition-fast);
}

.upload-card.loading { cursor: wait; pointer-events: none; }

.upload-card:hover:not(.loading) {
  border-color: rgba(164, 213, 255, 0.82);
  background: linear-gradient(155deg, rgba(14, 25, 44, 0.94), rgba(9, 17, 30, 0.95));
  box-shadow: var(--shadow-glow);
}

.upload-card:focus-within {
  border-color: var(--accent);
  box-shadow: var(--focus-ring);
}

.upload-card input {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
  pointer-events: none;
}

.upload-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  color: #d5ebff;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-light);
  border-top-color: var(--state-loading);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.upload-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto 1rem;
  color: #9bb5de;
  transition: color var(--transition-fast);
}

.upload-card:hover:not(.loading) .upload-icon { color: var(--accent-hover); }
.upload-icon svg { width: 100%; height: 100%; }

.upload-text {
  font-size: clamp(1rem, 1.2vw, 1.1rem);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.upload-hint {
  font-size: clamp(0.8rem, 1vw, 0.85rem);
  color: var(--text-muted);
}

.parse-msg { margin-top: 0; color: var(--text-secondary); }
.upload-feedback { margin-top: 0.75rem; }

.variable-pool {
  background: var(--surface-elevated);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-md);
  padding: 1rem;
  box-shadow: var(--shadow-sm);
}

.pool-summary {
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin-bottom: 0.75rem;
}

.var-search {
  width: 100%;
  margin-bottom: 0.75rem;
}

.var-list {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 360px;
  overflow-y: auto;
}

.var-item {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid rgba(118, 154, 214, 0.2);
  font-size: 0.9rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.var-item.high-missing {
  background: linear-gradient(90deg, rgba(240, 122, 134, 0.12), rgba(240, 122, 134, 0.04));
}

.var-name { font-weight: 500; color: var(--text-primary); }
.var-meta { font-size: 0.8rem; color: var(--text-muted); }
.var-meta .missing { color: #ffc3cb; }

.type-override { display: inline-flex; align-items: center; }
.type-select {
  color: var(--text-secondary);
}

.no-match { padding: 1rem; color: var(--text-muted); font-size: 0.9rem; }

.placeholder-box {
  padding: 2rem;
  background: var(--surface-elevated);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-md);
  text-align: center;
  color: var(--text-muted);
  font-size: 0.9rem;
  box-shadow: var(--shadow-sm);
}

.sidebar {
  display: grid;
  gap: var(--osem-block-gap, 0.82rem);
}

.sidebar-section {
  padding: 0.85rem 0.9rem;
}

.format-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.format-list li {
  padding: 0.5rem 0;
  border-bottom: 1px solid rgba(114, 150, 210, 0.2);
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.ext {
  font-family: var(--font-ui);
  font-weight: 600;
  color: var(--accent-cta);
  margin-right: 0.5rem;
}

.sidebar-tip {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-bottom: 0.65rem;
  line-height: 1.6;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(2, 5, 11, 0.72);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: var(--surface-elevated);
  padding: 1.5rem;
  max-width: 400px;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-glow);
}

.modal h4 { margin-bottom: 0.75rem; font-size: 1.1rem; }
.modal p { margin-bottom: 0.5rem; font-size: 0.9rem; color: var(--text-secondary); }
.modal-hint { font-size: 0.8rem; color: var(--text-muted); margin-top: 0.5rem; }

.data-missing-confirm {
  margin-top: 1rem;
}

.missing-options {
  margin-top: 0.9rem;
  display: grid;
  gap: 0.6rem;
}

.opt {
  display: grid;
  grid-template-columns: 18px 1fr;
  column-gap: 0.6rem;
  row-gap: 0.1rem;
  align-items: start;
  padding: 0.6rem 0.65rem;
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-sm);
  background: rgba(19, 28, 46, 0.78);
}

.opt input { margin-top: 0.2rem; }

.opt-title {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 0.9rem;
}

.opt-desc {
  grid-column: 2 / 3;
  color: var(--text-muted);
  font-size: 0.82rem;
}

@media (max-width: 768px) {
  .view-layout { grid-template-columns: 1fr; }
}

@media (prefers-reduced-motion: reduce) {
  .spinner {
    animation: none;
    border-top-color: var(--line-strong);
  }
}
</style>
