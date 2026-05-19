import { describe, expect, it } from 'vitest'
import { bootstrapEffectTypeLabel, fmtSequence } from './bootstrapDisplay'

describe('fmtSequence', () => {
  it('数组应连接为箭头路径', () => {
    expect(fmtSequence(['X', 'M', 'Y'])).toBe('X → M → Y')
  })

  it('非数组应返回占位符', () => {
    expect(fmtSequence(null)).toBe('—')
    expect(fmtSequence(undefined)).toBe('—')
    expect(fmtSequence('not-array')).toBe('—')
  })
})

describe('bootstrapEffectTypeLabel', () => {
  it('已知 effect_type 应返回对应中文标签', () => {
    expect(bootstrapEffectTypeLabel('total_indirect')).toBe('总间接')
    expect(bootstrapEffectTypeLabel('direct_effect')).toBe('直接效应')
    expect(bootstrapEffectTypeLabel('total_effect')).toBe('总效应')
  })

  it('未知类型应归为特定间接', () => {
    expect(bootstrapEffectTypeLabel('other')).toBe('特定间接')
    expect(bootstrapEffectTypeLabel(null)).toBe('特定间接')
  })
})
