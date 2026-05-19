export function getFilenameFromHeaders(headers, fallback) {
  const cd = headers?.['content-disposition'] || headers?.['Content-Disposition']
  if (!cd) return fallback

  const utf8 = cd.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8?.[1]) {
    try {
      return decodeURIComponent(utf8[1])
    } catch (_) {
      // invalid URL-encoded filename should fallback to plain filename
    }
  }

  const plain = cd.match(/filename="?([^"]+)"?/i)
  return plain?.[1] || fallback
}
