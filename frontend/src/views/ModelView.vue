<template>
  <div class="model-view osem-core-page" :style="corePageStyle">
    <section class="section reveal" :style="{ transitionDelay: '0ms' }">
      <h3 class="section-label">STRUCTURAL FORM MODELING / 表单建模</h3>
      <div class="section-rule"></div>
      <p class="lead osem-core-intro">
        先完成潜变量、路径与误差协变设定，再一键生成 lavaan 语法。
      </p>
      <div v-if="!dataStore.dataKey" :class="[FEEDBACK.base, resolveFeedbackTone('empty')]">
        <p :class="FEEDBACK.text">建模前缺少数据会话</p>
        <p :class="FEEDBACK.detail">请先在数据管理页面上传数据，获取 data_key 后再建模。</p>
      </div>
    </section>

    <section class="section reveal" :style="{ transitionDelay: '80ms' }">
      <h3 class="section-label">CFA / 潜变量设定</h3>
      <div class="section-rule"></div>
      <p class="hint">潜变量 <TermTip ns="model" term="latent_var" /> 由多个观测指标共同测量。</p>
      <div class="panel">
        <div class="inline">
          <input v-model="newLatentName" :class="INP.input" placeholder="潜变量名称，如 SAT" />
          <button type="button" :class="BTN.secondary" @click="addLatentVar">新增潜变量</button>
        </div>
        <div v-if="latentVars.length === 0" class="placeholder">尚未添加潜变量</div>
        <div v-for="(lv, idx) in latentVars" :key="`lv-${idx}`" class="latent-card">
          <div class="latent-head">
            <strong>{{ lv.name }}</strong>
            <button class="link danger" @click="removeLatentVar(idx)">删除</button>
          </div>
          <p class="hint">选择题项（至少 2 个），首个题项将固定载荷 1.0</p>
          <p v-if="lv.indicators?.length > 8" class="nonblock-warn">
            指标数量较多（{{ lv.indicators.length }} 个）。可考虑拆分子维度（非阻断提示）。
          </p>
          <div class="chips">
            <label v-for="v in dataStore.variables" :key="`${lv.name}-${v.name}`" class="chip">
              <input type="checkbox" :value="v.name" v-model="lv.indicators" />
              <span>{{ v.name }}</span>
            </label>
          </div>
        </div>
      </div>
    </section>

    <section class="section reveal" :style="{ transitionDelay: '160ms' }">
      <h3 class="section-label">PATH / 路径设定</h3>
      <div class="section-rule"></div>
      <p class="hint">结构路径 <TermTip ns="model" term="path" /> 用于表达变量间因果/预测关系。</p>
      <div class="panel">
        <div class="inline">
          <select v-model="pathForm.from_var" :class="INP.select">
            <option value="">自变量</option>
            <option v-for="v in allSymbols" :key="`from-${v}`" :value="v">{{ v }}</option>
          </select>
          <span class="arrow">→</span>
          <select v-model="pathForm.to_var" :class="INP.select">
            <option value="">因变量</option>
            <option v-for="v in allSymbols" :key="`to-${v}`" :value="v">{{ v }}</option>
          </select>
          <button type="button" :class="BTN.secondary" @click="addPath">新增路径</button>
        </div>
        <ul class="list">
          <li v-for="(p, idx) in paths" :key="`p-${idx}`">
            <span>{{ p.from_var }} → {{ p.to_var }}</span>
            <button class="link danger" @click="removePath(idx)">删除</button>
          </li>
        </ul>
      </div>
    </section>

    <section class="section reveal" :style="{ transitionDelay: '240ms' }">
      <h3 class="section-label">ERROR COV / 误差协变</h3>
      <div class="section-rule"></div>
      <p class="hint">误差协变 <TermTip ns="model" term="error_covariance" /> 建议基于理论或修正指数谨慎添加。</p>
      <div class="panel">
        <div class="inline">
          <select v-model="covForm.left" :class="INP.select">
            <option value="">误差项 A</option>
            <option v-for="v in observedForCov" :key="`cov-l-${v}`" :value="v">{{ v }}</option>
          </select>
          <span class="arrow">~~</span>
          <select v-model="covForm.right" :class="INP.select">
            <option value="">误差项 B</option>
            <option v-for="v in observedForCov" :key="`cov-r-${v}`" :value="v">{{ v }}</option>
          </select>
          <button type="button" :class="BTN.secondary" @click="addCovariance">新增协变</button>
        </div>
        <ul class="list">
          <li v-for="(c, idx) in errorCovariances" :key="`c-${idx}`">
            <span>{{ c[0] }} ~~ {{ c[1] }}</span>
            <button class="link danger" @click="removeCovariance(idx)">删除</button>
          </li>
        </ul>
      </div>
    </section>

    <section class="section reveal" :style="{ transitionDelay: '300ms' }">
      <h3 class="section-label">LATENT INTERACTION / 潜变量交互</h3>
      <div class="section-rule"></div>
      <p class="hint">
        边界：OpenSEM 使用 semopy 估计；请在语法中显式写出乘积潜变量或交互项。以下为乘积指标骨架（需数据表先具备 P1… 列），可追加到 lavaan 后再手改。
      </p>
      <div class="inline inline-latent-interaction">
        <input v-model.trim="liF1" :class="[INP.input, 'li-input-short']" placeholder="潜变量 F1" />
        <input v-model.trim="liF2" :class="[INP.input, 'li-input-short']" placeholder="潜变量 F2" />
        <input v-model.trim="liY" :class="[INP.input, 'li-input-long']" placeholder="结局（潜变量或观测）" />
        <button
          type="button"
          :class="BTN.secondary"
          :disabled="!liF1 || !liF2 || !liY || liSnippetLoading"
          @click="fetchLatentInteractionSnippet"
        >
          {{ liSnippetLoading ? '请求中…' : '追加交互骨架到语法' }}
        </button>
      </div>
      <p v-if="liSnippetError" class="error-text">{{ liSnippetError }}</p>
    </section>

    <section class="section reveal" :style="{ transitionDelay: '320ms' }">
      <h3 class="section-label">BUILD / 校验与转译</h3>
      <div class="section-rule"></div>
      <div class="inline">
        <button
          type="button"
          :class="BTN.secondary"
          :disabled="modelStore.validating || !dataStore.dataKey"
          @click="validateModel"
        >
          {{ modelStore.validating ? '校验中…' : '校验模型' }}
        </button>
        <button
          type="button"
          :class="BTN.primary"
          :disabled="modelStore.building || !dataStore.dataKey"
          @click="buildLavaan"
        >
          {{ modelStore.building ? '转换中…' : '生成 lavaan 语法' }}
        </button>
        <button type="button" :class="BTN.secondary" :disabled="!canCopyForm" @click="copyFormJson">
          复制表单 JSON
        </button>
        <button type="button" :class="BTN.secondary" :disabled="!modelStore.lavaanSyntax" @click="copyLavaanSyntax">
          复制 lavaan
        </button>
      </div>
      <div v-if="buildFeedback.length" class="feedback-list">
        <div
          v-for="(f, idx) in buildFeedback"
          :key="`feedback-${idx}`"
          :class="[FEEDBACK.base, resolveFeedbackTone(f.kind), 'feedback-item']"
        >
          <p :class="FEEDBACK.text">{{ f.text }}</p>
          <p :class="FEEDBACK.detail">{{ f.detail }}</p>
        </div>
      </div>
      <textarea
        ref="syntaxBoxEl"
        v-model="modelStore.lavaanSyntax"
        :class="[INP.textareaMono, 'syntax-box']"
        rows="10"
        placeholder="这里会显示 lavaan 语法"
        readonly
      />
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDataStore } from '../stores/dataStore'
import { useModelStore } from '../stores/modelStore'
import { api } from '../api/client'
import TermTip from '../components/TermTip.vue'
import { BTN } from '../ui/buttonContract.js'
import { INP } from '../ui/inputContract.js'
import { useNoticeStore } from '../stores/noticeStore'
import { useDialogStore } from '../stores/dialogStore'
import { joinErrorMessage } from '../utils/errorPresenter'
import { requestUserConfirm } from '../utils/uiFeedback'
import { resolveBuildFeedback } from './model/buildFeedback'
import { FEEDBACK, resolveFeedbackTone } from '../ui/feedbackContract.js'
import { useOsemCorePageStyle } from './core/useOsemCorePageStyle'

const STORAGE_KEY = 'OpenSEM:model-form:v1'

const dataStore = useDataStore()
const modelStore = useModelStore()
const noticeStore = useNoticeStore()
const dialogStore = useDialogStore()
const router = useRouter()
const route = useRoute()

const syntaxBoxEl = ref(null)
const { corePageStyle } = useOsemCorePageStyle('model')

function focusSyntaxBox() {
  const el = syntaxBoxEl.value
  if (!el) return
  try {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  } catch (_) {
    // ignore
  }
  el.classList.add('syntax-flash')
  setTimeout(() => el.classList.remove('syntax-flash'), 900)
}

const newLatentName = ref('')
const latentVars = ref([])
const paths = ref([])
const errorCovariances = ref([])

const pathForm = reactive({ from_var: '', to_var: '' })
const covForm = reactive({ left: '', right: '' })

const latentNames = computed(() => latentVars.value.map((lv) => lv.name))
const canCopyForm = computed(
  () => latentVars.value.length > 0 || paths.value.length > 0 || errorCovariances.value.length > 0
)
const observedForCov = computed(() => {
  const selected = new Set()
  for (const lv of latentVars.value) {
    for (const ind of lv.indicators) selected.add(ind)
  }
  return [...selected]
})
const allSymbols = computed(() => {
  const observed = dataStore.variables.map((v) => v.name)
  return [...new Set([...latentNames.value, ...observed])]
})
const copyToast = ref('')
let copyTimer = null

const liF1 = ref('F1')
const liF2 = ref('F2')
const liY = ref('Y')
const liSnippetLoading = ref(false)
const liSnippetError = ref('')
const buildFeedback = computed(() =>
  resolveBuildFeedback({
    copyToast: copyToast.value,
    error: modelStore.error,
    warnings: modelStore.warnings,
  })
)

function warn(message) {
  noticeStore.push({ type: 'warning', title: '输入检查', message, timeoutMs: 4200 })
}

async function fetchLatentInteractionSnippet() {
  liSnippetError.value = ''
  const f1 = liF1.value.trim()
  const f2 = liF2.value.trim()
  const y = liY.value.trim()
  if (!f1 || !f2 || !y) {
    liSnippetError.value = '请填写 F1、F2 与结局变量名'
    return
  }
  liSnippetLoading.value = true
  try {
    const { data } = await api.post('/api/v1/model/latent-interaction-snippet', {
      f1,
      f2,
      outcome: y,
      n_products: 3,
    })
    const sn = String(data?.lavaan_snippet || '').trim()
    if (!sn) {
      liSnippetError.value = '未返回语法片段'
      return
    }
    modelStore.appendLavaanSnippet(sn)
    copyToast.value = '已追加潜变量交互骨架（请检查 P1… 列与变量名）'
    if (copyTimer) clearTimeout(copyTimer)
    copyTimer = setTimeout(() => {
      copyToast.value = ''
    }, 3200)
    focusSyntaxBox()
  } catch (e) {
    liSnippetError.value = joinErrorMessage(e, '请求失败')
  } finally {
    liSnippetLoading.value = false
  }
}

function saveFormPersisted() {
  const payload = {
    newLatentName: newLatentName.value,
    latentVars: latentVars.value,
    paths: paths.value,
    errorCovariances: errorCovariances.value,
    pathForm: { ...pathForm },
    covForm: { ...covForm },
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
}

function clearFormPersisted() {
  localStorage.removeItem(STORAGE_KEY)
}

function loadFormPersisted() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const d = JSON.parse(raw)
    newLatentName.value = d.newLatentName || ''
    latentVars.value = Array.isArray(d.latentVars) ? d.latentVars : []
    paths.value = Array.isArray(d.paths) ? d.paths : []
    errorCovariances.value = Array.isArray(d.errorCovariances) ? d.errorCovariances : []
    pathForm.from_var = d.pathForm?.from_var || ''
    pathForm.to_var = d.pathForm?.to_var || ''
    covForm.left = d.covForm?.left || ''
    covForm.right = d.covForm?.right || ''
  } catch (_) {
    clearFormPersisted()
  }
}

function addLatentVar() {
  const name = newLatentName.value.trim()
  if (!name) return
  if (latentVars.value.some((lv) => lv.name === name)) {
    warn('潜变量名称已存在')
    return
  }
  latentVars.value.push({ name, indicators: [] })
  newLatentName.value = ''
}

function removeLatentVar(idx) {
  latentVars.value.splice(idx, 1)
}

async function addPath() {
  if (!pathForm.from_var || !pathForm.to_var) return
  if (pathForm.from_var === pathForm.to_var) {
    warn('路径起点和终点不能相同')
    return
  }
  const sameExists = paths.value.some(
    (p) => p.from_var === pathForm.from_var && p.to_var === pathForm.to_var
  )
  if (sameExists) {
    warn('该路径已存在')
    return
  }
  const inverseExists = paths.value.some(
    (p) => p.from_var === pathForm.to_var && p.to_var === pathForm.from_var
  )
  if (inverseExists) {
    const ok = await requestUserConfirm(dialogStore, {
      title: '双向路径确认',
      message: '检测到双向路径，是否继续添加？',
      confirmText: '继续添加',
      cancelText: '取消',
    })
    if (!ok) return
  }
  paths.value.push({ from_var: pathForm.from_var, to_var: pathForm.to_var })
  pathForm.from_var = ''
  pathForm.to_var = ''
}

function removePath(idx) {
  paths.value.splice(idx, 1)
}

function addCovariance() {
  if (!covForm.left || !covForm.right) return
  if (covForm.left === covForm.right) {
    warn('误差协变两端不能相同')
    return
  }
  const hasDup = errorCovariances.value.some((pair) => {
    return (
      (pair[0] === covForm.left && pair[1] === covForm.right) ||
      (pair[0] === covForm.right && pair[1] === covForm.left)
    )
  })
  if (hasDup) {
    warn('该误差协变已存在')
    return
  }

  const degree = {}
  for (const pair of errorCovariances.value) {
    degree[pair[0]] = (degree[pair[0]] || 0) + 1
    degree[pair[1]] = (degree[pair[1]] || 0) + 1
  }
  if ((degree[covForm.left] || 0) >= 3 || (degree[covForm.right] || 0) >= 3) {
    warn('单个误差项最多允许 3 条协变关系')
    return
  }

  errorCovariances.value.push([covForm.left, covForm.right])
  covForm.left = ''
  covForm.right = ''
}

function removeCovariance(idx) {
  errorCovariances.value.splice(idx, 1)
}

function getPayload() {
  return {
    data_key: dataStore.dataKey,
    latent_vars: latentVars.value,
    paths: paths.value,
    error_covariances: errorCovariances.value,
  }
}

async function validateModel() {
  await modelStore.validateModel(getPayload())
}

async function buildLavaan() {
  await modelStore.buildLavaan(getPayload())
}

function showCopyToast(msg) {
  copyToast.value = msg
  if (copyTimer) clearTimeout(copyTimer)
  copyTimer = setTimeout(() => {
    copyToast.value = ''
    copyTimer = null
  }, 1800)
}

async function copyFormJson() {
  const text = JSON.stringify(getPayload(), null, 2)
  try {
    await navigator.clipboard.writeText(text)
    showCopyToast('已复制表单 JSON')
  } catch (_) {
    showCopyToast('复制失败，请检查剪贴板权限')
  }
}

async function copyLavaanSyntax() {
  const text = modelStore.lavaanSyntax || ''
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    showCopyToast('已复制 lavaan 语法')
  } catch (_) {
    showCopyToast('复制失败，请检查剪贴板权限')
  }
}

onMounted(() => {
  document.querySelector('.model-view')?.classList.add('visible')
  loadFormPersisted()
  dataStore.validatePersistedDataKey().then((res) => {
    if (res?.valid === false) {
      latentVars.value = []
      paths.value = []
      errorCovariances.value = []
      newLatentName.value = ''
      pathForm.from_var = ''
      pathForm.to_var = ''
      covForm.left = ''
      covForm.right = ''
      clearFormPersisted()
      noticeStore.push({
        type: 'error',
        title: '会话失效',
        message: '检测到数据会话已过期，请先重新上传数据。',
        timeoutMs: 5500,
      })
    }
  })

  // 从 Results 页跳转过来时可高亮 lavaan 语法框
  if (route?.query?.focus === 'syntax') {
    nextTick(() => focusSyntaxBox())
    // 清掉 query，避免刷新后反复触发
    router.replace({ path: route.path, query: {} }).catch(() => {})
  }
})

watch(
  [newLatentName, latentVars, paths, errorCovariances, () => pathForm.from_var, () => pathForm.to_var, () => covForm.left, () => covForm.right],
  () => {
    saveFormPersisted()
  },
  { deep: true }
)
</script>

<style scoped>
.model-view {
  --osem-core-bg-nebula-a: rgba(98, 169, 247, 0.18);
  --osem-core-bg-nebula-b: rgba(245, 159, 103, 0.12);
  --osem-core-bg-nebula-c: rgba(128, 151, 245, 0.15);
  padding: var(--osem-core-outer-pad, clamp(1.5rem, 3vw, 2.5rem));
  max-width: 980px;
}

.section-label {
  margin-bottom: 0.5rem;
}

.section-rule {
  height: 1px;
  background: var(--line-soft);
  margin-bottom: 1rem;
}

.lead { font-size: 0.95rem; color: var(--text-secondary); margin-bottom: 0.75rem; }
.panel {
  background: var(--surface-elevated);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-md);
  padding: 1rem;
  box-shadow: var(--shadow-sm);
}

.inline {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
}

.inline .osem-input,
.inline .osem-select {
  min-width: 200px;
}

.inline-latent-interaction {
  gap: 0.5rem;
}

.li-input-short {
  width: 8rem;
  min-width: 8rem;
}

.li-input-long {
  width: 14rem;
  min-width: 14rem;
}

.latent-card {
  border-top: 1px solid rgba(116, 154, 214, 0.22);
  padding-top: 0.7rem;
  margin-top: 0.7rem;
}

.latent-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.25rem;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem 0.65rem;
}

.chip {
  font-size: 0.84rem;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.22rem 0.4rem;
  border-radius: 999px;
  border: 1px solid rgba(114, 150, 210, 0.24);
  background: rgba(22, 37, 65, 0.48);
}

.list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.list li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid rgba(116, 154, 214, 0.22);
  padding: 0.5rem 0;
  font-size: 0.9rem;
}

.link {
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--accent);
}

.link:hover { color: var(--accent-hover); }
.link.danger { color: #ffb3be; }
.link.danger:hover { color: #ffd0d7; }
.arrow { color: var(--text-muted); font-family: var(--font-ui); }
.placeholder { font-size: 0.88rem; color: var(--text-muted); }
.hint { font-size: 0.82rem; color: var(--text-muted); margin-bottom: 0.55rem; }
.nonblock-warn { font-size: 0.82rem; color: #f0c987; margin: 0.25rem 0 0.55rem; }
.error-text { color: var(--error); margin: 0.4rem 0; font-size: 0.88rem; }

.feedback-list {
  display: grid;
  gap: 0.45rem;
  margin: 0.4rem 0 0.6rem;
}

.feedback-item { margin-top: 0; }

.syntax-box {
  width: 100%;
  padding: 0.65rem;
  resize: vertical;
}

.syntax-box.syntax-flash {
  outline: 2px solid var(--accent);
  box-shadow: 0 0 0 6px rgba(139, 200, 255, 0.16);
}

@media (max-width: 700px) {
  .inline .osem-input,
  .inline .osem-select {
    min-width: 160px;
  }

  .li-input-short,
  .li-input-long {
    width: 100%;
    min-width: 160px;
  }
}
</style>
