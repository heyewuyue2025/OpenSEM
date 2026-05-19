export function buildInvSeriesCardText({
  comparison,
  badge,
  degraded = false,
  fmtP,
  isNA,
} = {}) {
  const c = comparison && typeof comparison === 'object' ? comparison : {}
  const toNum = (v) => {
    const n = Number(v)
    return Number.isFinite(n) ? n : null
  }

  const dcfi = toNum(c.delta_cfi)
  const drmsea = toNum(c.delta_rmsea)
  const evidenceParts = []
  evidenceParts.push(dcfi === null ? 'ΔCFI=NA' : `ΔCFI=${Number(dcfi).toFixed(4)}`)
  evidenceParts.push(drmsea === null ? 'ΔRMSEA=NA' : `ΔRMSEA=${Number(drmsea).toFixed(4)}`)

  const hasFmtP = typeof fmtP === 'function'
  const hasIsNA = typeof isNA === 'function'
  const pIsNA = hasIsNA ? isNA(c.p_value) : c.p_value === null || c.p_value === undefined
  if (!pIsNA) evidenceParts.push(`p=${hasFmtP ? fmtP(c.p_value) : String(c.p_value)}`)

  const threshold = degraded ? '—（降级）' : '|ΔCFI| < 0.01 且 |ΔRMSEA| < 0.015'

  let reason = ''
  if (degraded) {
    reason = '当前环境未启用 lavaan 或 LRT 不可用：该序列结果仅作占位提示，不可用于论文级等值结论。'
  } else if (badge === 'PASS') {
    reason = '两项拟合度变化均低于常用经验阈值，通常可认为该步等值约束可接受。'
  } else if (badge === 'FAIL') {
    reason = '至少一项拟合度变化超过常用经验阈值，提示该步等值约束可能不成立（建议结合理论与模型修正）。'
  } else {
    reason = '缺少关键指标，无法按经验阈值判断（可能未收敛或 lavTestLRT 不可用）。'
  }

  return {
    threshold,
    evidence: evidenceParts.join(' · '),
    reason,
  }
}
