import { describe, expect, it } from 'vitest'
import { resolveHeroReadability } from './heroReadability'

describe('resolveHeroReadability', () => {
  it('空输入时返回桌面默认态可读性参数', () => {
    expect(resolveHeroReadability()).toEqual({
      quoteWeight: 720,
      quoteLineHeight: 1.22,
      subtitleLineHeight: 1.8,
      subtitleMaxWidth: '700px',
      assistiveLineHeight: 1.68,
      blockGap: '0.9rem',
    })
  })

  it('非法输入时回退默认参数（失败兜底）', () => {
    expect(resolveHeroReadability('bad-input')).toEqual({
      quoteWeight: 720,
      quoteLineHeight: 1.22,
      subtitleLineHeight: 1.8,
      subtitleMaxWidth: '700px',
      assistiveLineHeight: 1.68,
      blockGap: '0.9rem',
    })
  })
})
