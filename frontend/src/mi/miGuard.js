function safeStr(v) {
  return String(v ?? '').trim()
}

function toNum(v) {
  if (v === null || v === undefined) return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

export function normalizeMiItem(raw) {
  const lhs = safeStr(raw?.lhs)
  const op = safeStr(raw?.op)
  const rhs = safeStr(raw?.rhs)
  const mi = toNum(raw?.mi)
  const epc = toNum(raw?.epc)
  const kind = safeStr(raw?.kind)
  const risk = safeStr(raw?.risk)
  return { lhs, op, rhs, mi, epc, kind, risk, raw: raw && typeof raw === 'object' ? raw : {} }
}

function normalizeSyntax(s) {
  return String(s || '')
    .split('\n')
    .map((row) => row.split('#')[0].trim())
    .filter(Boolean)
    .join('\n')
}

function parseRegressionPairsFromSyntax(syntax) {
  // very small parser: only handles "lhs ~ rhs1 + rhs2" style
  const pairs = new Set()
  const rows = normalizeSyntax(syntax).split('\n')
  for (const row of rows) {
    const m = row.match(/^(.+?)\s*~\s*(.+)$/)
    if (!m) continue
    const lhs = safeStr(m[1])
    const rhsPart = safeStr(m[2])
    if (!lhs || !rhsPart) continue
    const rhsTokens = rhsPart
      .split('+')
      .map((x) => safeStr(x))
      .filter(Boolean)
    for (const rhs of rhsTokens) {
      pairs.add(`${lhs}::${rhs}`)
    }
  }
  return pairs
}

export function evaluateMiGuard({
  miItem,
  adoptionCount = 0,
  currentSyntax = '',
  thresholds = { autoRefitAdoptionCap: 5 },
} = {}) {
  const it = normalizeMiItem(miItem)
  const adoptionN = Math.max(0, Number(adoptionCount || 0))
  const cap = Number(thresholds.autoRefitAdoptionCap ?? 5)

  // 风险分层（最小可用、可扩展）：先复刻现有逻辑
  const isHighRisk =
    it.risk === 'high' ||
    it.kind === 'cross_loading' ||
    it.op === '=~' || // 交叉载荷
    it.op === '~~' // 误差协方差（产品门禁按高风险处理，避免误用）

  // 方向冲突（高风险）：若当前语法中存在 rhs ~ lhs，但候选是 lhs ~ rhs
  let hasDirectionConflict = false
  if (it.op === '~' && it.lhs && it.rhs) {
    const pairs = parseRegressionPairsFromSyntax(currentSyntax)
    if (pairs.has(`${it.rhs}::${it.lhs}`)) {
      hasDirectionConflict = true
    }
  }

  const confirmations = []

  if (hasDirectionConflict) {
    confirmations.push({
      id: 'direction_conflict',
      message:
        `检测到方向冲突：当前模型中已存在路径 ${it.rhs} ~ ${it.lhs}，而本条建议为 ${it.lhs} ~ ${it.rhs}。\n\n该类修正风险较高，建议回到理论框架核对因果方向后再决定是否重估。\n\n仍要“追加并立即重估”吗？`,
      defaultOnCancel: 'apply_only',
    })
  }

  if (isHighRisk) {
    confirmations.push({
      id: 'high_risk',
      message:
        '该条 MI 风险较高（例如交叉载荷/潜在方向不明确）。\n\n建议：先仅追加到语法与表单草稿，回到建模页检查合理性后再手动重新估算。\n\n仍要“追加并立即重估”吗？',
      defaultOnCancel: 'apply_only',
    })
  }

  // 超过阈值：直接禁止自动重估（安全默认），不提供“强行继续”选项
  const allowAutoRefit = adoptionN < cap
  if (!allowAutoRefit) {
    confirmations.push({
      id: 'adoption_cap_block',
      message:
        `你已累计采纳 ${adoptionN} 条 MI。\n\n为避免过拟合，已默认禁用“采纳并重算”。建议：先仅追加到草稿并回到理论框架检查每条修正，之后手动重估。`,
      defaultOnCancel: 'apply_only',
    })
  }

  if (allowAutoRefit) {
    confirmations.push({
      id: 'final_refit',
      message: '将采纳该条 MI 并立即重新估算（会清空旧结果）。继续？',
      defaultOnCancel: 'abort',
    })
  }

  const riskTier = isHighRisk ? 'high' : it.risk === 'low' ? 'low' : 'medium'

  return {
    item: it,
    riskTier,
    allowAutoRefit,
    confirmations,
  }
}

