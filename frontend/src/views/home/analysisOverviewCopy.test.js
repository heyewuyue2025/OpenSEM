import { describe, expect, it } from 'vitest'
import { resolveAnalysisOverviewCopy } from './analysisOverviewCopy'

describe('resolveAnalysisOverviewCopy', () => {
  it('空输入时返回 ANALYSIS OVERVIEW 默认词典', () => {
    expect(resolveAnalysisOverviewCopy()).toEqual({
      sectionLabel: 'ANALYSIS OVERVIEW / 分析概览',
      metrics: [
        { key: 'sampleN', label: '样本量 Sample N' },
        { key: 'latent', label: '潜变量数量' },
        { key: 'cfi', label: '拟合指标 CFI' },
      ],
    })
  })

  it('将历史同义术语收敛为 ANALYSIS OVERVIEW 词典口径（失败兜底）', () => {
    const copy = resolveAnalysisOverviewCopy({
      metrics: [
        { key: 'sampleN', label: '样本量 N' },
        { key: 'latent', label: '潜变量 Latent' },
        { key: 'cfi', label: '拟合 CFI' },
      ],
    })

    expect(copy.metrics).toEqual([
      { key: 'sampleN', label: '样本量 Sample N' },
      { key: 'latent', label: '潜变量数量' },
      { key: 'cfi', label: '拟合指标 CFI' },
    ])
  })
})
