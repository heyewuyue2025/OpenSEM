import { describe, expect, it } from 'vitest'
import { resolveQuickStartRhythm } from './quickStartRhythm'

describe('resolveQuickStartRhythm', () => {
  it('空输入时返回 QUICK START 默认节奏参数', () => {
    expect(resolveQuickStartRhythm()).toEqual({
      labelGap: '0.65rem',
      cardGap: '0.9rem',
      titleLineHeight: 1.35,
      summaryLineHeight: 1.7,
      summaryMaxWidth: '62ch',
      linkTopGap: '0.9rem',
    })
  })

  it('非法输入时回退默认节奏参数（失败兜底）', () => {
    expect(resolveQuickStartRhythm('bad-input')).toEqual({
      labelGap: '0.65rem',
      cardGap: '0.9rem',
      titleLineHeight: 1.35,
      summaryLineHeight: 1.7,
      summaryMaxWidth: '62ch',
      linkTopGap: '0.9rem',
    })
  })
})
