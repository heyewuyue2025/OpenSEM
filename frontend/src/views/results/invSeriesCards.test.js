import { describe, expect, it } from 'vitest'
import { buildInvSeriesCardText } from './invSeriesCards'
import { isNA } from './isNA'

describe('invSeriesCards helpers', () => {
  it('builds threshold/evidence/reason for pass step', () => {
    const card = buildInvSeriesCardText({
      comparison: { delta_cfi: 0.0012, delta_rmsea: -0.0026, p_value: 0.031 },
      badge: 'PASS',
      degraded: false,
      fmtP: (v) => Number(v).toFixed(3),
      isNA,
    })

    expect(card.threshold).toBe('|ΔCFI| < 0.01 且 |ΔRMSEA| < 0.015')
    expect(card.evidence).toContain('ΔCFI=0.0012')
    expect(card.evidence).toContain('ΔRMSEA=-0.0026')
    expect(card.evidence).toContain('p=0.031')
    expect(card.reason).toContain('低于常用经验阈值')
  })

  it('falls back to degraded threshold and NA evidence on invalid input', () => {
    const card = buildInvSeriesCardText({
      comparison: { delta_cfi: 'bad', delta_rmsea: null, p_value: null },
      badge: 'UNKNOWN',
      degraded: true,
      fmtP: () => 'unused',
      isNA: () => true,
    })

    expect(card.threshold).toBe('—（降级）')
    expect(card.evidence).toBe('ΔCFI=NA · ΔRMSEA=0.0000')
    expect(card.reason).toContain('仅作占位提示')
  })
})
