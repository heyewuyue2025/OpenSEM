import { describe, expect, it } from 'vitest'
import { explainFitMetric, formatFitMetricValue } from './fitIndicesMetric'

describe('formatFitMetricValue', () => {
  it('成功：有数值时转为字符串展示', () => {
    expect(formatFitMetricValue('cfi', { cfi: 0.951 })).toBe('0.951')
  })

  it('边界：无拟合对象或缺字段时为占位', () => {
    expect(formatFitMetricValue('cfi', null)).toBe('—')
    expect(formatFitMetricValue('cfi', {})).toBe('—')
  })
})

describe('explainFitMetric', () => {
  it('成功：有有效数值时返回分档解释文案', () => {
    expect(explainFitMetric('chi2_df', { chi2_df: 2.5 })).toContain('通常认为拟合较好')
    expect(explainFitMetric('rmsea', { rmsea: 0.05 })).toContain('近似误差较小')
  })

  it('边界：无 fit 或无法解析数值时的提示', () => {
    expect(explainFitMetric('cfi', null)).toBe('运行估算后解释会出现在这里')
    expect(explainFitMetric('cfi', { cfi: '-' })).toBe('未能计算该指标（可能与样本/模型有关）')
  })
})
