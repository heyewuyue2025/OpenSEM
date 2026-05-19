import { describe, expect, it } from 'vitest'
import { computeInvSeriesConclusionLevel } from './invConclusionLevel'

function badgeByKey(c) {
  const key = `${String(c?.from || '').trim()}::${String(c?.to || '').trim()}`
  const passKeys = new Set(['configural::metric', 'metric::scalar', 'scalar::strict'])
  return { badge: passKeys.has(key) ? 'PASS' : 'FAIL' }
}

describe('invConclusionLevel helpers', () => {
  it('returns strict success when all steps pass', () => {
    const r = computeInvSeriesConclusionLevel({
      lite: false,
      degraded: false,
      comparisons: [
        { from: 'configural', to: 'metric' },
        { from: 'metric', to: 'scalar' },
        { from: 'scalar', to: 'strict' },
      ],
      getStepBadge: badgeByKey,
    })
    expect(r).toMatchObject({ level: 'strict', ok: true })
  })

  it('returns lite metric when scalar step fails', () => {
    const r = computeInvSeriesConclusionLevel({
      lite: true,
      degraded: false,
      comparisons: [
        { from: 'configural', to: 'metric' },
        { from: 'metric', to: 'scalarX' },
      ],
      getStepBadge: (c) => {
        const key = `${String(c?.from || '').trim()}::${String(c?.to || '').trim()}`
        return { badge: key === 'configural::metric' ? 'PASS' : 'FAIL' }
      },
    })
    expect(r).toMatchObject({ level: 'metric', ok: true })
  })

  it('returns NA for degraded or empty comparisons', () => {
    expect(
      computeInvSeriesConclusionLevel({
        degraded: true,
        comparisons: [{ from: 'configural', to: 'metric' }],
        getStepBadge: badgeByKey,
      })
    ).toMatchObject({ level: 'NA', ok: null, note: 'degraded' })

    expect(
      computeInvSeriesConclusionLevel({
        degraded: false,
        comparisons: [],
        getStepBadge: badgeByKey,
      })
    ).toMatchObject({ level: 'NA', ok: null, note: 'no comparisons' })
  })
})
