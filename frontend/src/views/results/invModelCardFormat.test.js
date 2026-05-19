import { describe, expect, it } from 'vitest'
import { formatInvModelMetric4 } from './invModelCardFormat'

describe('formatInvModelMetric4', () => {
  it('returns fixed 4 decimals for numeric input', () => {
    expect(formatInvModelMetric4(0.123456)).toBe('0.1235')
  })

  it('returns NA for null input', () => {
    expect(formatInvModelMetric4(null)).toBe('NA')
  })

  it('keeps Number(...).toFixed behavior for non-numeric input', () => {
    expect(formatInvModelMetric4(undefined)).toBe('NaN')
  })
})
