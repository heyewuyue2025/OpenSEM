import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'

const STORAGE_KEY = 'opensem:data:v1'

export const useDataStore = defineStore('data', () => {
  const variables = ref([])
  const nRows = ref(0)
  const nCols = ref(0)
  const dataKey = ref(null)
  const parseMessage = ref(null)
  const highMissingWarning = ref(false)
  const missingStrategy = ref('') // '' 表示未选择
  const loading = ref(false)
  const error = ref(null)
  const sessionInvalidWarning = ref('')

  function _detailText(e, fallback) {
    const detail = e?.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (detail && typeof detail === 'object') return detail?.message || fallback || ''
    return e?.message || fallback || ''
  }

  function savePersisted() {
    const payload = {
      variables: variables.value,
      nRows: nRows.value,
      nCols: nCols.value,
      dataKey: dataKey.value,
      parseMessage: parseMessage.value,
      highMissingWarning: highMissingWarning.value,
      missingStrategy: missingStrategy.value,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  }

  function loadPersisted() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return
      const d = JSON.parse(raw)
      variables.value = d.variables || []
      nRows.value = d.nRows || 0
      nCols.value = d.nCols || 0
      dataKey.value = d.dataKey || null
      parseMessage.value = d.parseMessage || null
      highMissingWarning.value = Boolean(d.highMissingWarning)
      missingStrategy.value = d.missingStrategy || ''
    } catch (_) {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  async function parseFile(file) {
    loading.value = true
    error.value = null
    variables.value = []
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await api.post('/api/v1/data/parse', formData, { timeout: 30000 })
      const d = res.data
      variables.value = (d.variables || []).map((v) => ({ ...v, user_type: v.type || '' }))
      nRows.value = d.n_rows || 0
      nCols.value = d.n_cols || 0
      dataKey.value = d.data_key || null
      parseMessage.value = d.message || null
      highMissingWarning.value = d.high_missing_warning || false
      missingStrategy.value = '' // 每次新上传强制重新选择
      sessionInvalidWarning.value = ''
      savePersisted()
      return d
    } catch (e) {
      error.value = _detailText(e, '解析失败')
      throw e
    } finally {
      loading.value = false
    }
  }

  function setVariableType(name, nextType) {
    const idx = variables.value.findIndex((v) => v.name === name)
    if (idx < 0) return
    variables.value[idx] = { ...variables.value[idx], user_type: nextType }
    savePersisted()
  }

  function setMissingStrategy(v) {
    missingStrategy.value = v
    savePersisted()
  }

  function clearData() {
    variables.value = []
    nRows.value = 0
    nCols.value = 0
    dataKey.value = null
    parseMessage.value = null
    highMissingWarning.value = false
    missingStrategy.value = ''
    error.value = null
    sessionInvalidWarning.value = ''
    savePersisted()
  }

  async function validatePersistedDataKey() {
    if (!dataKey.value) return { valid: true }
    try {
      const { data } = await api.post('/api/v1/data/validate-key', { data_key: dataKey.value })
      if (data.valid) {
        sessionInvalidWarning.value = ''
        return { valid: true }
      }
      const oldKey = dataKey.value
      clearData()
      sessionInvalidWarning.value = `检测到 data_key 已失效（${oldKey.slice(0, 8)}...），请重新上传数据。`
      return { valid: false }
    } catch (e) {
      // 后端不可达时不强制清空，避免误删本地进度
      return { valid: true, skipped: true, reason: e.message }
    }
  }

  loadPersisted()

  return {
    variables,
    nRows,
    nCols,
    dataKey,
    parseMessage,
    highMissingWarning,
    missingStrategy,
    loading,
    error,
    sessionInvalidWarning,
    parseFile,
    setVariableType,
    setMissingStrategy,
    clearData,
    validatePersistedDataKey,
  }
})
