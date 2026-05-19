import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'
import { useDataStore } from './dataStore'
import { useStatsStore } from './statsStore'

const STORAGE_KEY = 'OpenSEM:model:v1'
const MODEL_FORM_STORAGE_KEY = 'OpenSEM:model-form:v1'

export const useModelStore = defineStore('model', () => {
  const dataStore = useDataStore()
  const statsStore = useStatsStore()
  const lavaanSyntax = ref('')
  const warnings = ref([])
  // MI 产品化：累计采纳次数（用于过拟合防护提示）
  const miAdoptionCount = ref(0)
  const validating = ref(false)
  const building = ref(false)
  const error = ref(null)

  function _normalizeApiError(e, fallback) {
    const detail = e?.response?.data?.detail
    if (typeof detail === 'string') return { code: '', message: detail, hint: '' }
    if (detail && typeof detail === 'object') {
      return {
        code: String(detail.code || '').trim(),
        message: String(detail.message || '').trim() || (fallback || ''),
        hint: String(detail.hint || '').trim(),
      }
    }
    return { code: '', message: e?.message || fallback || '', hint: '' }
  }

  function _isDataKeyInvalid(err) {
    const code = String(err?.code || '').trim()
    const msg = String(err?.message || '').trim()
    return code === 'DATA_KEY_INVALID' || msg.includes('data_key 无效')
  }

  function savePersisted() {
    const payload = {
      lavaanSyntax: lavaanSyntax.value,
      warnings: warnings.value,
      miAdoptionCount: miAdoptionCount.value,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  }

  function _normalizeSyntax(s) {
    return String(s || '')
      .split('\n')
      .map((row) => row.trim())
      .filter(Boolean)
      .join('\n')
  }

  function loadPersisted() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return
      const d = JSON.parse(raw)
      lavaanSyntax.value = d.lavaanSyntax || ''
      warnings.value = d.warnings || []
      miAdoptionCount.value = Number.isFinite(Number(d.miAdoptionCount)) ? Number(d.miAdoptionCount) : 0
    } catch (_) {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  async function validateModel(payload) {
    validating.value = true
    error.value = null
    try {
      const { data } = await api.post('/api/v1/model/validate', payload)
      warnings.value = data.warnings || []
      savePersisted()
      return data
    } catch (e) {
      const err = _normalizeApiError(e, '模型校验失败')
      if (_isDataKeyInvalid(err)) {
        dataStore.clearData()
        clearModelResult()
        error.value = '当前数据会话已过期，请先重新上传数据再建模。'
        throw e
      }
      error.value = err.message || '模型校验失败'
      throw e
    } finally {
      validating.value = false
    }
  }

  async function buildLavaan(payload) {
    building.value = true
    error.value = null
    try {
      const before = _normalizeSyntax(lavaanSyntax.value)
      const { data } = await api.post('/api/v1/model/to-lavaan', payload)
      lavaanSyntax.value = data.lavaan_syntax || ''
      warnings.value = data.warnings || []
      const after = _normalizeSyntax(lavaanSyntax.value)
      if (before && after && before !== after) {
        // 语法已发生变化：清空旧结果，避免“旧结果配新语法”误导解读/导出
        statsStore.clearAllResults()
      }
      savePersisted()
      return data
    } catch (e) {
      const err = _normalizeApiError(e, 'lavaan 转换失败')
      if (_isDataKeyInvalid(err)) {
        dataStore.clearData()
        clearModelResult()
        error.value = '当前数据会话已过期，请先重新上传数据再生成语法。'
        throw e
      }
      error.value = err.message || 'lavaan 转换失败'
      throw e
    } finally {
      building.value = false
    }
  }

  function clearModelResult() {
    lavaanSyntax.value = ''
    warnings.value = []
    error.value = null
    miAdoptionCount.value = 0
    savePersisted()
  }

  function setLavaanSyntax(next) {
    const before = _normalizeSyntax(lavaanSyntax.value)
    lavaanSyntax.value = String(next ?? '')
    const after = _normalizeSyntax(lavaanSyntax.value)
    if (before && after && before !== after) {
      statsStore.clearAllResults()
    }
    savePersisted()
  }

  function decrementMiAdoptionCount() {
    miAdoptionCount.value = Math.max(0, Number(miAdoptionCount.value || 0) - 1)
    savePersisted()
  }

  function _readModelFormPersisted() {
    try {
      const raw = localStorage.getItem(MODEL_FORM_STORAGE_KEY)
      if (!raw) return null
      const d = JSON.parse(raw)
      return d && typeof d === 'object' ? d : null
    } catch (_) {
      return null
    }
  }

  function _writeModelFormPersisted(next) {
    try {
      localStorage.setItem(MODEL_FORM_STORAGE_KEY, JSON.stringify(next))
      return true
    } catch (_) {
      return false
    }
  }

  function readModelFormPersisted() {
    return _readModelFormPersisted()
  }

  function writeModelFormPersisted(next) {
    return _writeModelFormPersisted(next)
  }

  function _hasVariableName(name) {
    const n = String(name || '').trim()
    if (!n) return false
    return (dataStore.variables || []).some((v) => String(v?.name || '').trim() === n)
  }

  function _normalizeMi(it) {
    const lhs = String(it?.lhs ?? '').trim()
    const op = String(it?.op ?? '').trim()
    const rhs = String(it?.rhs ?? '').trim()
    return { lhs, op, rhs }
  }

  /**
   * 尝试将 MI 建议同步写回“表单建模”持久化状态（ModelView.vue 使用 localStorage 保存）。
   * 能同步的范围（最小可用）：
   * - `lhs =~ rhs`：若 lhs 是已存在潜变量，且 rhs 是数据变量，则追加到该潜变量 indicators
   * - `lhs ~ rhs`：追加路径 rhs -> lhs（from_var=rhs,to_var=lhs）
   * - `lhs ~~ rhs`：若两端都是“已入模的观测指标”，追加到 errorCovariances（去重）
   *
   * @returns {{ ok: true, applied: boolean, message: string } | { ok: false, message: string }}
   */
  function applyMiToModelFormPersisted(it) {
    const { lhs, op, rhs } = _normalizeMi(it)
    if (!lhs || !op || !rhs) return { ok: false, message: 'MI 项缺少 lhs/op/rhs，无法同步表单' }

    const d = _readModelFormPersisted()
    if (!d) return { ok: true, applied: false, message: '未发现建模表单草稿（将仅追加到语法）' }

    const latentVars = Array.isArray(d.latentVars) ? d.latentVars : []
    const paths = Array.isArray(d.paths) ? d.paths : []
    const errorCovariances = Array.isArray(d.errorCovariances) ? d.errorCovariances : []

    // 构造“当前已入模的观测指标集合”（与 ModelView 的 observedForCov 一致：来自 latentVars.indicators）
    const observedSelected = new Set()
    for (const lv of latentVars) {
      const inds = Array.isArray(lv?.indicators) ? lv.indicators : []
      for (const x of inds) observedSelected.add(String(x || '').trim())
    }

    if (op === '=~') {
      // lavaan: latent =~ indicator
      const lvIdx = latentVars.findIndex((lv) => String(lv?.name || '').trim() === lhs)
      if (lvIdx < 0) {
        return { ok: true, applied: false, message: `未在表单中找到潜变量 ${lhs}（将仅追加到语法）` }
      }
      if (!_hasVariableName(rhs)) {
        return { ok: true, applied: false, message: `数据中不存在变量 ${rhs}（将仅追加到语法）` }
      }
      const inds = Array.isArray(latentVars[lvIdx].indicators) ? latentVars[lvIdx].indicators : []
      const exists = inds.some((x) => String(x || '').trim() === rhs)
      if (exists) return { ok: true, applied: false, message: `表单中已包含该交叉载荷（${lhs} =~ ${rhs}）` }
      latentVars[lvIdx] = { ...latentVars[lvIdx], indicators: [...inds, rhs] }
      const ok = _writeModelFormPersisted({ ...d, latentVars })
      return ok
        ? { ok: true, applied: true, message: `已同步到表单：为潜变量 ${lhs} 追加指标 ${rhs}` }
        : { ok: false, message: '写入表单草稿失败（localStorage 不可用）' }
    }

    if (op === '~') {
      // lavaan: lhs ~ rhs  => rhs -> lhs
      const from = rhs
      const to = lhs
      const fromOk = _hasVariableName(from) || latentVars.some((lv) => String(lv?.name || '').trim() === from)
      const toOk = _hasVariableName(to) || latentVars.some((lv) => String(lv?.name || '').trim() === to)
      if (!fromOk || !toOk) {
        return { ok: true, applied: false, message: '该回归路径涉及未知符号（将仅追加到语法）' }
      }
      const sameExists = paths.some((p) => String(p?.from_var || '').trim() === from && String(p?.to_var || '').trim() === to)
      if (sameExists) return { ok: true, applied: false, message: `表单中已包含该路径（${from} → ${to}）` }
      paths.push({ from_var: from, to_var: to })
      const ok = _writeModelFormPersisted({ ...d, paths })
      return ok
        ? { ok: true, applied: true, message: `已同步到表单：新增路径 ${from} → ${to}` }
        : { ok: false, message: '写入表单草稿失败（localStorage 不可用）' }
    }

    if (op === '~~') {
      // 只同步“误差协变”到表单：要求两端都是已入模观测指标
      if (!observedSelected.has(lhs) || !observedSelected.has(rhs)) {
        return {
          ok: true,
          applied: false,
          message: '误差协变仅支持对“已选择的观测题项”同步（将仅追加到语法）',
        }
      }
      const hasDup = errorCovariances.some((pair) => {
        const a = String(pair?.[0] || '').trim()
        const b = String(pair?.[1] || '').trim()
        return (a === lhs && b === rhs) || (a === rhs && b === lhs)
      })
      if (hasDup) return { ok: true, applied: false, message: `表单中已包含该误差协变（${lhs} ~~ ${rhs}）` }
      errorCovariances.push([lhs, rhs])
      const ok = _writeModelFormPersisted({ ...d, errorCovariances })
      return ok
        ? { ok: true, applied: true, message: `已同步到表单：新增误差协变 ${lhs} ~~ ${rhs}` }
        : { ok: false, message: '写入表单草稿失败（localStorage 不可用）' }
    }

    return { ok: true, applied: false, message: '该 MI 类型当前不支持同步到表单（将仅追加到语法）' }
  }

  /**
   * 将单条 lavaan 约束追加到当前语法（用于 MI 建议回填）。
   * @returns {{ ok: true, duplicate: boolean } | { ok: false, message: string }}
   */
  function appendLavaanLineFromMi({ lhs, op, rhs }) {
    const l = String(lhs ?? '').trim()
    const o = String(op ?? '').trim()
    const r = String(rhs ?? '').trim()
    if (!l || !o || !r) {
      return { ok: false, message: 'MI 项缺少 lhs、op 或 rhs' }
    }
    const newLine = `${l} ${o} ${r}`
    const normalized = newLine.replace(/\s+/g, ' ').trim()
    const body = (lavaanSyntax.value || '').trimEnd()
    const existing = body.split(/\n/).some((row) => {
      const t = row.split('#')[0].replace(/\s+/g, ' ').trim()
      return t === normalized
    })
    if (existing) {
      return { ok: true, duplicate: true }
    }
    const next = body.length ? `${body}\n${newLine}\n` : `${newLine}\n`
    lavaanSyntax.value = next
    miAdoptionCount.value = Math.max(0, Number(miAdoptionCount.value || 0)) + 1
    savePersisted()
    return { ok: true, duplicate: false }
  }

  function resetMiAdoptionCount() {
    miAdoptionCount.value = 0
    savePersisted()
  }

  /**
   * 追加自定义 lavaan 片段（如潜变量交互骨架）。会触发与修改语法一致的 STALE 清理。
   */
  function appendLavaanSnippet(block, { separator = '\n\n' } = {}) {
    const extra = String(block || '').trim()
    if (!extra) return
    const before = _normalizeSyntax(lavaanSyntax.value)
    const base = (lavaanSyntax.value || '').trimEnd()
    lavaanSyntax.value = base.length ? `${base}${separator}${extra}` : extra
    const after = _normalizeSyntax(lavaanSyntax.value)
    if (before && after && before !== after) {
      statsStore.clearAllResults()
    }
    savePersisted()
  }

  loadPersisted()

  return {
    lavaanSyntax,
    warnings,
    miAdoptionCount,
    validating,
    building,
    error,
    validateModel,
    buildLavaan,
    clearModelResult,
    setLavaanSyntax,
    applyMiToModelFormPersisted,
    appendLavaanLineFromMi,
    resetMiAdoptionCount,
    decrementMiAdoptionCount,
    readModelFormPersisted,
    writeModelFormPersisted,
    appendLavaanSnippet,
  }
})
