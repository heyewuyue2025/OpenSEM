import { describe, expect, it } from 'vitest'
import { evaluateMiGuard } from './miGuard'

describe('evaluateMiGuard', () => {
  it('adds high_risk confirmation for cross_loading', () => {
    const r = evaluateMiGuard({
      miItem: { lhs: 'F1', op: '=~', rhs: 'q9', kind: 'cross_loading', risk: 'high' },
      adoptionCount: 0,
    })
    expect(r.confirmations.some((x) => x.id === 'high_risk')).toBe(true)
  })

  it('adds adoption_cap confirmation when adoptionCount >= 5', () => {
    const r = evaluateMiGuard({
      miItem: { lhs: 'y', op: '~', rhs: 'x', kind: 'regression', risk: 'medium' },
      adoptionCount: 3,
      thresholds: { autoRefitAdoptionCap: 3 },
    })
    expect(r.allowAutoRefit).toBe(false)
    expect(r.confirmations.some((x) => x.id === 'adoption_cap_block')).toBe(true)
  })

  it('always includes final_refit confirmation', () => {
    const r = evaluateMiGuard({
      miItem: { lhs: 'y', op: '~', rhs: 'x' },
      adoptionCount: 0,
    })
    expect(r.confirmations.at(-1)?.id).toBe('final_refit')
  })

  it('flags direction conflict when reverse path exists in syntax', () => {
    const r = evaluateMiGuard({
      miItem: { lhs: 'y', op: '~', rhs: 'x' },
      adoptionCount: 0,
      currentSyntax: 'x ~ y\n',
    })
    expect(r.confirmations.some((x) => x.id === 'direction_conflict')).toBe(true)
  })

  it('treats ~~ as high risk and asks confirmation', () => {
    const r = evaluateMiGuard({
      miItem: { lhs: 'q1', op: '~~', rhs: 'q2' },
      adoptionCount: 0,
    })
    expect(r.riskTier).toBe('high')
    expect(r.confirmations.some((x) => x.id === 'high_risk')).toBe(true)
  })
})

