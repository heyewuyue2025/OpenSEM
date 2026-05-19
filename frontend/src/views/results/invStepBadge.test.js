import { describe, expect, it } from 'vitest'
import { computeInvStepBadge } from './invStepBadge.js'

describe('computeInvStepBadge', () => {
  it('在阈值内且未降级时返回 PASS', () => {
    const r = computeInvStepBadge({ delta_cfi: 0.005, delta_rmsea: 0.01 }, { degraded: false })
    expect(r.badge).toBe('PASS')
    expect(r.status).toBe('pass')
    expect(r.note).toMatch(/\|ΔCFI\|=/)
  })

  it('超出经验阈值时返回 FAIL', () => {
    const r = computeInvStepBadge({ delta_cfi: 0.02, delta_rmsea: 0.02 }, { degraded: false })
    expect(r.badge).toBe('FAIL')
    expect(r.status).toBe('fail')
  })

  it('降级结果固定为不可比', () => {
    const r = computeInvStepBadge({ delta_cfi: 0, delta_rmsea: 0 }, { degraded: true })
    expect(r.badge).toBe('—')
    expect(r.note).toContain('降级')
  })

  it('缺少 Δ 指标且无 note 时列出缺失项', () => {
    const r = computeInvStepBadge({}, { degraded: false })
    expect(r.badge).toBe('—')
    expect(r.note).toContain('ΔCFI')
    expect(r.note).toContain('ΔRMSEA')
  })
})
