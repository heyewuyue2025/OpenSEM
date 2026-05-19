import { describe, expect, it } from 'vitest'
import { normalizeSyntax, shortTag } from './syntaxFingerprint'

describe('syntaxFingerprint helpers', () => {
  it('normalizes multiline syntax and removes blank rows', () => {
    const raw = '  y ~ x  \n\n  m ~ x \n'
    expect(normalizeSyntax(raw)).toBe('y ~ x\nm ~ x')
  })

  it('falls back to empty string for invalid normalize input', () => {
    expect(normalizeSyntax(null)).toBe('')
  })

  it('generates stable short tag for same input', () => {
    const a = shortTag('y ~ x\nm ~ x')
    const b = shortTag('y ~ x\nm ~ x')
    expect(a).toBe(b)
    expect(a.length).toBeGreaterThanOrEqual(7)
  })

  it('falls back to empty-input hash when tag input is null', () => {
    expect(shortTag(null)).toBe(shortTag(''))
  })
})
