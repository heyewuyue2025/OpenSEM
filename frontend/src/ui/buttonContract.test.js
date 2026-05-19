import { describe, it, expect } from 'vitest'
import { BTN, pickButtonVariant } from './buttonContract.js'

describe('buttonContract', () => {
  it('每个变体均包含基础类名 osem-btn', () => {
    for (const cls of Object.values(BTN)) {
      expect(cls).toMatch(/\bosem-btn\b/)
    }
  })

  it('pickButtonVariant：合法 key 返回对应变体', () => {
    expect(pickButtonVariant('primary')).toBe(BTN.primary)
    expect(pickButtonVariant('ghost')).toBe(BTN.ghost)
  })

  it('pickButtonVariant：非法或缺失 key 回退到 secondary（失败兜底）', () => {
    expect(pickButtonVariant('not-a-variant')).toBe(BTN.secondary)
    expect(pickButtonVariant()).toBe(BTN.secondary)
    expect(pickButtonVariant('')).toBe(BTN.secondary)
  })
})
