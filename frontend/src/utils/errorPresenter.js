export function normalizeApiError(input, fallback = '') {
  const detail = input?.response?.data?.detail
  if (typeof detail === 'string') {
    return { code: '', message: detail, hint: '' }
  }
  if (detail && typeof detail === 'object') {
    return {
      code: String(detail.code || '').trim(),
      message: String(detail.message || '').trim() || String(fallback || '').trim(),
      hint: String(detail.hint || '').trim(),
    }
  }
  return {
    code: '',
    message: String(input?.message || fallback || '').trim(),
    hint: '',
  }
}

export function joinErrorMessage(err, fallback = '') {
  const normalized = normalizeApiError(err, fallback)
  const message = normalized.message || String(fallback || '').trim() || '请求失败'
  const hint = normalized.hint ? `提示：${normalized.hint}` : ''
  return [message, hint].filter(Boolean).join(' ')
}

