/**
 * 将表格/API 混用的字符串与数字安全解析为有限数值；缺失占位与非法输入统一为 null。
 * 供 Results 与 pathSummary 等模块复用，避免静默分叉。
 */
export function toNum(v) {
  if (v === null || v === undefined || v === '-') return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}
