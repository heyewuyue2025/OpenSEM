import { describe, expect, it } from 'vitest'
import { fmt, fmtCi, fmtP } from './formatters'

describe('results formatters helpers', () => {
  it('formats numeric and boundary p values', () => {
    expect(fmt(0.125)).toBe('0.125')
    expect(fmtP(0.0004)).toBe('<0.001')
    expect(fmtP(0.02)).toBe('0.02')
  })

  it('returns fallback marker for missing inputs', () => {
    expect(fmt(null)).toBe('—')
    expect(fmtP(undefined)).toBe('—')
    expect(fmtCi(null)).toBe('—')
    expect(fmtCi({ lo: null, hi: 0.2 })).toBe('—')
  })

  it('keeps non-numeric values unchanged', () => {
    expect(fmt('NA')).toBe('NA')
    expect(fmtP('p<0.05')).toBe('p<0.05')
  })

  it('formats CI with lo and hi when both exist', () => {
    expect(fmtCi({ lo: -0.12, hi: 0.38 })).toBe('[-0.12, 0.38]')
  })
})
