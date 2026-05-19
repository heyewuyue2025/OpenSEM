import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '../api/client'

const STORAGE_KEY = 'OpenSEM:runtime-health:v1'

function _safeString(v) {
  const s = String(v ?? '').trim()
  return s
}

export const useRuntimeStore = defineStore('runtime', () => {
  const loading = ref(false)
  const error = ref('')
  const lastFetchedAt = ref('')
  const health = ref(null)

  const mode = computed(() => _safeString(health.value?.mode) || 'unknown')
  const requireLavaan = computed(() => Boolean(health.value?.require_lavaan))
  const withLavaan = computed(() => {
    const raw = health.value?.with_lavaan
    return raw === null || raw === undefined ? null : Boolean(raw)
  })
  const lavaanAvailable = computed(() => Boolean(health.value?.lavaan?.available))
  const lavaanReason = computed(() => _safeString(health.value?.lavaan?.reason) || '')

  const lavaanMessage = computed(() => {
    if (lavaanAvailable.value) {
      return mode.value === 'strict'
        ? '当前已启用 lavaan（strict），MI / 不变性序列可用。'
        : '当前已启用 lavaan（lite），MI / 不变性序列可用。'
    }
    const reason = lavaanReason.value ? `原因：${lavaanReason.value}` : '原因：未知'
    if (requireLavaan.value) {
      return `当前为 strict（强制 lavaan）。${reason}。请先修复后端 R/lavaan/rpy2 环境。`
    }
    return `当前为 lite（允许降级）。${reason}。如需启用 MI/不变性序列：使用 Docker strict 模式或安装 R + lavaan + rpy2。`
  })

  function savePersisted() {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          lastFetchedAt: lastFetchedAt.value,
          health: health.value,
        })
      )
    } catch (_) {
      // ignore
    }
  }

  function loadPersisted() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return
      const d = JSON.parse(raw)
      health.value = d?.health ?? null
      lastFetchedAt.value = d?.lastFetchedAt ?? ''
    } catch (_) {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  async function refreshHealth() {
    if (loading.value) return health.value
    loading.value = true
    error.value = ''
    try {
      const { data } = await api.get('/api/health')
      health.value = data
      lastFetchedAt.value = new Date().toISOString()
      savePersisted()
      return data
    } catch (e) {
      // strict 模式下 lavaan 不可用会返回 503，但响应体依然包含结构化 health
      const maybeBody = e?.response?.data
      if (maybeBody && typeof maybeBody === 'object') {
        health.value = maybeBody
        lastFetchedAt.value = new Date().toISOString()
        savePersisted()
        return maybeBody
      }
      error.value = _safeString(e?.message) || 'health 请求失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    lastFetchedAt,
    health,
    mode,
    requireLavaan,
    withLavaan,
    lavaanAvailable,
    lavaanReason,
    lavaanMessage,
    loadPersisted,
    refreshHealth,
  }
})

