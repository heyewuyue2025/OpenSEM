import { describe, expect, it } from 'vitest'
import { resolveQuickStartResponsive } from './quickStartResponsive'

describe('resolveQuickStartResponsive', () => {
  it('空输入时返回 768/375 默认响应式参数', () => {
    expect(resolveQuickStartResponsive()).toEqual({
      tablet768: {
        summaryMaxWidth: '56ch',
        cardPadding: '1.25rem',
        visualHeight: '108px',
      },
      mobile375: {
        labelGap: '0.5rem',
        cardGap: '0.7rem',
        titleLineHeight: 1.3,
        summaryLineHeight: 1.62,
        summaryMaxWidth: '34ch',
        linkTopGap: '0.65rem',
        cardPadding: '1rem',
        visualHeight: '92px',
      },
    })
  })

  it('非法输入时回退默认参数（失败兜底）', () => {
    expect(resolveQuickStartResponsive('bad-input')).toEqual({
      tablet768: {
        summaryMaxWidth: '56ch',
        cardPadding: '1.25rem',
        visualHeight: '108px',
      },
      mobile375: {
        labelGap: '0.5rem',
        cardGap: '0.7rem',
        titleLineHeight: 1.3,
        summaryLineHeight: 1.62,
        summaryMaxWidth: '34ch',
        linkTopGap: '0.65rem',
        cardPadding: '1rem',
        visualHeight: '92px',
      },
    })
  })
})
