export function looksLikeErrorTerm(name) {
  const n = String(name || '').trim().toLowerCase()
  return /^e\d+$/.test(n) || n.startsWith('err') || n.startsWith('resid') || n.startsWith('.')
}

export function inferMiKind(it) {
  const op = String(it?.op || '').trim()
  const lhs = String(it?.lhs || '').trim()
  const rhs = String(it?.rhs || '').trim()
  if (op === '=~') return { kind: 'cross_loading', label: '交叉载荷' }
  if (op === '~') return { kind: 'regression', label: '回归路径' }
  if (op === '~~') {
    if (looksLikeErrorTerm(lhs) || looksLikeErrorTerm(rhs)) {
      return { kind: 'residual_cov', label: '残差协方差' }
    }
    return { kind: 'covariance', label: '协方差' }
  }
  return { kind: 'other', label: '其他' }
}

export function inferMiRisk(it, allItems) {
  const op = String(it?.op || '').trim()
  const lhs = String(it?.lhs || '').trim()
  const rhs = String(it?.rhs || '').trim()
  const { kind } = inferMiKind(it)
  if (kind === 'cross_loading') {
    return { risk: 'high', label: '高' }
  }
  if (op === '~') {
    const hasReverse = (allItems || []).some((x) => {
      return String(x?.op || '').trim() === '~' &&
        String(x?.lhs || '').trim() === rhs &&
        String(x?.rhs || '').trim() === lhs
    })
    if (hasReverse) return { risk: 'high', label: '高' }
    return { risk: 'medium', label: '中' }
  }
  if (kind === 'residual_cov') return { risk: 'low', label: '低' }
  if (kind === 'covariance') return { risk: 'medium', label: '中' }
  return { risk: 'medium', label: '中' }
}
