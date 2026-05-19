import { describe, expect, it } from 'vitest'
import { buildInvOneLineConclusion } from './invConclusion'

describe('invConclusion helpers', () => {
  it('returns strict pass sentence when strict conclusion is ok', () => {
    const text = buildInvOneLineConclusion({
      conclusion: { level: 'strict', ok: true },
      lite: false,
    })
    expect(text).toContain('一句话结论（strict）')
    expect(text).toContain('达到 strict 不变性')
  })

  it('returns lite fail sentence when level is below scalar', () => {
    const text = buildInvOneLineConclusion({
      conclusion: { level: 'metric', ok: false },
      lite: true,
    })
    expect(text).toContain('一句话结论（lite）')
    expect(text).toContain('未能支持到 scalar/strict')
    expect(text).toContain('metric')
  })

  it('falls back to NA sentence for invalid input', () => {
    const text = buildInvOneLineConclusion({ conclusion: null, lite: true })
    expect(text).toContain('测量不变性序列结果不足')
  })
})
