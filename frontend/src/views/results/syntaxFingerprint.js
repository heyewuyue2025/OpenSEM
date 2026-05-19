export function normalizeSyntax(s) {
  return String(s || '')
    .split('\n')
    .map((row) => row.trim())
    .filter(Boolean)
    .join('\n')
}

export function shortTag(s) {
  // FNV-1a 32-bit, 仅用于界面短标签，不用于安全场景
  let h = 0x811c9dc5
  const str = String(s || '')
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i)
    h = (h * 0x01000193) >>> 0
  }
  return h.toString(36).padStart(7, '0')
}
