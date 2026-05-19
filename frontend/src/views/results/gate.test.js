import { describe, expect, it } from 'vitest'
import { normalizeGate } from './gate'

describe('gate helpers', () => {
  it('returns supported gate when override supported=true', () => {
    const r = normalizeGate({ mode: '', message: '' }, { supported: true, modeWhenSupported: 'lavaan' })
    expect(r).toMatchObject({
      supported: true,
      mode: 'lavaan',
      message: '',
      degraded: false,
    })
  })

  it('returns degraded gate with fallback message on invalid input', () => {
    const r = normalizeGate(null, { supported: false, fallbackMessageWhenDegraded: '降级提示' })
    expect(r).toMatchObject({
      supported: false,
      mode: 'degraded',
      message: '降级提示',
      degraded: true,
    })
  })

  it('uses raw supported/mode/message when provided', () => {
    const r = normalizeGate({ supported: false, mode: 'degraded', message: 'raw-msg' }, {})
    expect(r).toMatchObject({
      supported: false,
      mode: 'degraded',
      message: 'raw-msg',
      degraded: true,
    })
  })
})
