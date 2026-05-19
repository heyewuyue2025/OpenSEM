import { describe, expect, it } from 'vitest'
import { buildPathSummaryReportText, buildPathSummaryRows } from './pathSummary'

describe('pathSummary helpers', () => {
  it('buildPathSummaryRows returns sorted significant regression rows', () => {
    const rows = buildPathSummaryRows([
      { op: '~', lval: 'Y', rval: 'X1', est_std: 0.62, p_value: 0.001 },
      { op: '~', lval: 'Y', rval: 'X2', est_std: 0.15, p_value: 0.2 },
      { op: '=~', lval: 'F1', rval: 'x1', est_std: 0.8, p_value: 0.001 },
      { op: '~', lval: 'Y', rval: 'X3', estimate: -0.4, p_value: 0.03 },
    ])

    expect(rows).toHaveLength(3)
    expect(rows[0]).toMatchObject({ predictor: 'X1', outcome: 'Y', significant: true, direction: 'positive' })
    expect(rows[1]).toMatchObject({ predictor: 'X3', outcome: 'Y', significant: true, direction: 'negative' })
    expect(rows[2]).toMatchObject({ predictor: 'X2', outcome: 'Y', significant: false })
  })

  it('buildPathSummaryReportText returns no-path hint when no valid rows', () => {
    const report = buildPathSummaryReportText({
      estimates: [{ op: '=~', lval: 'F1', rval: 'x1', p_value: 0.1 }],
      nUsed: 128,
    })
    expect(report).toContain('样本量：N=128')
    expect(report).toContain('未在参数表中识别到可汇总的结构回归路径')
  })

  it('buildPathSummaryReportText includes significant path excerpt', () => {
    const report = buildPathSummaryReportText({
      estimates: [
        { op: '~', lval: 'Y', rval: 'X1', est_std: 0.51, p_value: 0.002 },
        { op: '~', lval: 'Y', rval: 'X2', est_std: -0.33, p_value: 0.04 },
      ],
      nUsed: 256,
    })
    expect(report).toContain('共识别到结构回归路径 2 条，其中显著 2 条。')
    expect(report).toContain('X1 → Y（β=0.510，p=0.002）')
  })
})
