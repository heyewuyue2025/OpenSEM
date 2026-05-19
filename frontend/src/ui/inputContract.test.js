import { describe, it, expect } from 'vitest'
import { INP, pickInputVariant } from './inputContract.js'

describe('inputContract', () => {
  it('基础控件类名以 osem- 为前缀', () => {
    expect(INP.input).toMatch(/\bosem-input\b/)
    expect(INP.select).toMatch(/\bosem-select\b/)
    expect(INP.textarea).toMatch(/\bosem-textarea\b/)
    expect(INP.fieldLabel).toMatch(/\bosem-field-label\b/)
  })

  it('selectCompact / textareaMono 组合包含修饰类', () => {
    expect(INP.selectCompact).toMatch(/\bosem-select--compact\b/)
    expect(INP.textareaMono).toMatch(/\bosem-textarea--mono\b/)
  })

  it('pickInputVariant：合法 key 返回对应契约串', () => {
    expect(pickInputVariant('select')).toBe(INP.select)
    expect(pickInputVariant('textarea')).toBe(INP.textarea)
  })

  it('pickInputVariant：非法或缺失 key 回退到 input（失败兜底）', () => {
    expect(pickInputVariant('not-a-key')).toBe(INP.input)
    expect(pickInputVariant()).toBe(INP.input)
    expect(pickInputVariant('')).toBe(INP.input)
  })
})
