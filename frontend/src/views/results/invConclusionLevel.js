export function computeInvSeriesConclusionLevel({
  comparisons,
  lite = false,
  degraded = false,
  getStepBadge,
} = {}) {
  if (degraded) return { level: 'NA', ok: null, note: 'degraded' }
  const comps = Array.isArray(comparisons) ? comparisons : []
  if (!comps.length) return { level: 'NA', ok: null, note: 'no comparisons' }

  const byKey = new Map()
  for (const c of comps) {
    const from = String(c?.from || '').trim()
    const to = String(c?.to || '').trim()
    if (!from || !to) continue
    byKey.set(`${from}::${to}`, c)
  }

  const pickBadge = (from, to) => {
    const fn = typeof getStepBadge === 'function' ? getStepBadge : () => ({})
    return fn(byKey.get(`${from}::${to}`) || {})
  }

  const metricB = pickBadge('configural', 'metric')
  const scalarB = pickBadge('metric', 'scalar')
  const strictB = pickBadge('scalar', 'strict')

  const metricOk = metricB?.badge === 'PASS'
  const scalarOk = metricOk && scalarB?.badge === 'PASS'
  const strictOk = scalarOk && strictB?.badge === 'PASS'

  if (lite) {
    if (scalarOk) return { level: 'scalar', ok: true, note: 'lite: up to scalar' }
    if (metricOk) return { level: 'metric', ok: true, note: 'lite: up to metric' }
    return { level: 'configural', ok: false, note: 'lite: metric not supported by thresholds' }
  }

  if (strictOk) return { level: 'strict', ok: true, note: 'strict: up to strict' }
  if (scalarOk) return { level: 'scalar', ok: false, note: 'strict: strict step failed' }
  if (metricOk) return { level: 'metric', ok: false, note: 'strict: scalar step failed' }
  return { level: 'configural', ok: false, note: 'strict: metric step failed' }
}
