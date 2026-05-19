/** 为单条 MI 建议项生成稳定键（与忽略列表、localStorage 持久化一致）。 */
export function miKey(it) {
  const l = String(it?.lhs ?? '').trim()
  const o = String(it?.op ?? '').trim()
  const r = String(it?.rhs ?? '').trim()
  return `${l}::${o}::${r}`
}
