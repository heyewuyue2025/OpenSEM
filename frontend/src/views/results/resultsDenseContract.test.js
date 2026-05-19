import { describe, expect, it } from 'vitest'
import { DENSE, resolveResultsDenseTokens, toDenseInlineStyleVars } from './resultsDenseContract'

describe('resultsDenseContract', () => {
  it('暴露稳定的 class 名', () => {
    expect(DENSE.rootModifier).toBe('osem-results-dense')
    expect(DENSE.zone).toBe('osem-dense-zone')
  })

  it('空输入时返回 768/375 默认可断言 token', () => {
    expect(resolveResultsDenseTokens()).toMatchObject({
      tablet768: expect.objectContaining({
        miListGap: '0.55rem',
        invCardLabelCol: '88px',
      }),
      mobile375: expect.objectContaining({
        miListGap: '0.5rem',
        estTableMinWidth: 'max(100%, 520px)',
      }),
    })
  })

  it('非法输入回退默认（失败兜底）', () => {
    expect(resolveResultsDenseTokens('x')).toEqual(resolveResultsDenseTokens())
  })

  it('toDenseInlineStyleVars 产出完整 CSS 变量键', () => {
    const vars = toDenseInlineStyleVars()
    expect(vars['--osem-dense-mi-list-gap-768']).toBe('0.55rem')
    expect(vars['--osem-dense-inv-pre-rem-375']).toBe(0.72)
  })
})
