import { describe, expect, it } from 'vitest'
import { buildInvModelFitLine } from './invModelFitLine.js'

describe('buildInvModelFitLine', () => {
  const toNum = (v) => {
    const n = Number(v)
    return Number.isFinite(n) ? n : null
  }

  it('成功：命中模型时输出四个拟合指标与收敛状态', () => {
    const line = buildInvModelFitLine({
      name: 'metric',
      models: [{ model: 'metric', converged: true, fit: { cfi: 0.93456, tli: 0.91, rmsea: 0.045, srmr: 0.055 } }],
      toNum,
    })
    expect(line).toContain('metric')
    expect(line).toContain('CFI=0.9346')
    expect(line).toContain('TLI=0.9100')
    expect(line).toContain('收敛')
  })

  it('边界：未命中模型或无效数值时走 NA 与未知状态', () => {
    const line = buildInvModelFitLine({
      name: 'strict',
      models: [{ model: 'configural', converged: false, fit: { cfi: '-' } }],
      toNum,
    })
    expect(line).toContain('strict')
    expect(line).toContain('CFI=NA')
    expect(line).toContain('RMSEA=NA')
    expect(line).toContain('未知')
  })
})
