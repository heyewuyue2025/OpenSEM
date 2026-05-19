/**
 * Bootstrap 结果表展示：效应类型文案与路径序列格式化（纯函数）。
 */

export function fmtSequence(sequence) {
  return Array.isArray(sequence) ? sequence.filter(Boolean).join(' → ') : '—'
}

export function bootstrapEffectTypeLabel(t) {
  if (t === 'total_indirect') return '总间接'
  if (t === 'direct_effect') return '直接效应'
  if (t === 'total_effect') return '总效应'
  return '特定间接'
}
