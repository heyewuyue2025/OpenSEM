import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useDialogStore = defineStore('dialog', () => {
  const current = ref(null)
  let resolver = null

  function clearWith(result) {
    const done = resolver
    resolver = null
    current.value = null
    if (typeof done === 'function') done(Boolean(result))
  }

  function confirm({
    title = '请确认',
    message = '',
    confirmText = '继续',
    cancelText = '取消',
  } = {}) {
    const msg = String(message || '').trim()
    if (!msg) return Promise.resolve(false)
    if (resolver) clearWith(false)
    return new Promise((resolve) => {
      resolver = resolve
      current.value = {
        type: 'confirm',
        title: String(title || '请确认').trim(),
        message: msg,
        confirmText: String(confirmText || '继续').trim() || '继续',
        cancelText: String(cancelText || '取消').trim() || '取消',
      }
    })
  }

  function accept() {
    clearWith(true)
  }

  function cancel() {
    clearWith(false)
  }

  return { current, confirm, accept, cancel }
})
