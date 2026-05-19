/**
 * 全局 notice 的 class 契约（单一来源，便于回归与命名一致）
 */
export const NOTICE = Object.freeze({
  base: 'osem-notice',
  title: 'osem-notice__title',
  message: 'osem-notice__message',
  close: 'osem-notice__close',
  toneError: 'osem-notice--error',
  toneWarning: 'osem-notice--warning',
  toneSuccess: 'osem-notice--success',
  toneInfo: 'osem-notice--info',
})

/**
 * @param {string} [type]
 * @returns {string}
 */
export function resolveNoticeTone(type) {
  const key = String(type || '').trim().toLowerCase()
  if (key === 'warning') return NOTICE.toneWarning
  if (key === 'success') return NOTICE.toneSuccess
  if (key === 'info') return NOTICE.toneInfo
  return NOTICE.toneError
}
