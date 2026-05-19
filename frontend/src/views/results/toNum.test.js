import { describe, expect, it } from 'vitest'
import { toNum } from './toNum'

describe('toNum', () => {
  it('解析有限数字与数字字符串为数值', () => {
    expect(toNum(0)).toBe(0)
    expect(toNum(-2.5)).toBe(-2.5)
    expect(toNum('0.04')).toBe(0.04)
    expect(toNum('  3.14  ')).toBe(3.14)
    expect(toNum('')).toBe(0)
  })

  it('对缺失占位、非有限值返回 null', () => {
    expect(toNum(null)).toBeNull()
    expect(toNum(undefined)).toBeNull()
    expect(toNum('-')).toBeNull()
    expect(toNum('not-a-number')).toBeNull()
    expect(toNum(Number.NaN)).toBeNull()
    expect(toNum(Number.POSITIVE_INFINITY)).toBeNull()
  })
})
