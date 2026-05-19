/**
 * 判定表格/API 混用值是否应视为缺失占位（与 Results 不变性卡片等展示语义一致）。
 */
export function isNA(v) {
  if (v === null || v === undefined) return true
  const s = String(v).trim()
  if (s === '' || s === '—' || s === '-') return true
  return s.toLowerCase() === 'na' || s.toLowerCase() === 'nan'
}
