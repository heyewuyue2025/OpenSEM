export function pushErrorNotice(noticeStore, message, title = '错误提示') {
  const msg = String(message || '').trim()
  if (!msg) return
  noticeStore?.push?.({
    type: 'error',
    title: String(title || '错误提示').trim() || '错误提示',
    message: msg,
    timeoutMs: 5200,
  })
}

export function pushWarningNotice(noticeStore, message, title = '操作提醒') {
  const msg = String(message || '').trim()
  if (!msg) return
  noticeStore?.push?.({
    type: 'warning',
    title: String(title || '操作提醒').trim() || '操作提醒',
    message: msg,
    timeoutMs: 4200,
  })
}

export async function requestUserConfirm(dialogStore, payload) {
  if (!dialogStore?.confirm) return false
  return dialogStore.confirm(payload)
}
