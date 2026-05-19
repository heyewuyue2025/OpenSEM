import { describe, expect, it } from 'vitest'
import { inferMiKind, inferMiRisk, looksLikeErrorTerm } from './miRisk'

describe('miRisk helpers', () => {
  it('classifies MI kind for cross-loading and residual covariance', () => {
    expect(inferMiKind({ op: '=~', lhs: 'F1', rhs: 'x3' })).toMatchObject({
      kind: 'cross_loading',
      label: '交叉载荷',
    })
    expect(inferMiKind({ op: '~~', lhs: 'e1', rhs: 'e2' })).toMatchObject({
      kind: 'residual_cov',
      label: '残差协方差',
    })
  })

  it('marks reverse regression pair as high risk', () => {
    const all = [
      { op: '~', lhs: 'Y', rhs: 'X' },
      { op: '~', lhs: 'X', rhs: 'Y' },
    ]
    expect(inferMiRisk(all[0], all)).toMatchObject({ risk: 'high', label: '高' })
  })

  it('falls back to safe defaults for invalid input', () => {
    expect(looksLikeErrorTerm('')).toBe(false)
    expect(inferMiKind(null)).toMatchObject({ kind: 'other', label: '其他' })
    expect(inferMiRisk(null, null)).toMatchObject({ risk: 'medium', label: '中' })
  })
})
