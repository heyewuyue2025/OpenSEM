import { defineStore } from 'pinia'
import { ref } from 'vue'

let seed = 0

export const useNoticeStore = defineStore('notice', () => {
  const current = ref(null)

  function push({ type = 'error', title = '', message = '', timeoutMs = 5000 } = {}) {
    const msg = String(message || '').trim()
    if (!msg) return null
    seed += 1
    const item = {
      id: `notice-${Date.now()}-${seed}`,
      type: String(type || 'error'),
      title: String(title || '').trim(),
      message: msg,
    }
    current.value = item
    if (timeoutMs > 0) {
      setTimeout(() => {
        if (current.value?.id === item.id) current.value = null
      }, timeoutMs)
    }
    return item
  }

  function dismiss() {
    current.value = null
  }

  return { current, push, dismiss }
})

