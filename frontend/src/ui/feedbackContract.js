export const FEEDBACK = Object.freeze({
  base: 'osem-feedback',
  text: 'osem-feedback-text',
  detail: 'osem-feedback-detail',
})

const SUPPORTED_KINDS = new Set(['loading', 'success', 'warning', 'error', 'empty'])

export function resolveFeedbackTone(kind) {
  const normalized = String(kind || '').trim().toLowerCase()
  if (!SUPPORTED_KINDS.has(normalized)) return 'is-warning'
  return `is-${normalized}`
}
