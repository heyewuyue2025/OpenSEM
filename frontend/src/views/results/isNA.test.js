import { describe, expect, it } from 'vitest'
import { isNA } from './isNA'

describe('isNA', () => {
  it('将常见缺失占位与 na/nan 字符串视为缺失', () => {
    expect(isNA(null)).toBe(true)
    expect(isNA(undefined)).toBe(true)
    expect(isNA('')).toBe(true)
    expect(isNA('  ')).toBe(true)
    expect(isNA('—')).toBe(true)
    expect(isNA('-')).toBe(true)
    expect(isNA('na')).toBe(true)
    expect(isNA('NA')).toBe(true)
    expect(isNA('nan')).toBe(true)
  })

  it('对有效数值与可展示字符串返回非缺失', () => {
    expect(isNA(0)).toBe(false)
    expect(isNA(0.031)).toBe(false)
    expect(isNA('0.031')).toBe(false)
    expect(isNA(' 0.04 ')).toBe(false)
  })
})
