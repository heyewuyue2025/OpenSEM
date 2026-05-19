function pickErrorDetail(detail) {
  if (typeof detail === 'string') return detail
  if (detail?.message) return detail.message
  return ''
}

export async function parseBlobError(error, fallback) {
  const data = error?.response?.data
  if (data instanceof Blob) {
    try {
      const text = await data.text()
      const parsed = JSON.parse(text)
      const parsedDetail = pickErrorDetail(parsed?.detail)
      if (parsedDetail) return parsedDetail
    } catch (_) {
      // ignore parse errors and fallback
    }
  }

  const directDetail = pickErrorDetail(data?.detail)
  if (directDetail) return directDetail
  return error?.message || fallback
}
