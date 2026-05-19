export function normalizeGate(raw, { supported, modeWhenSupported = 'lavaan', fallbackMessageWhenDegraded } = {}) {
  const r = raw && typeof raw === 'object' ? raw : {}
  const s = typeof supported === 'boolean' ? supported : typeof r.supported === 'boolean' ? r.supported : false
  const mode = String(r.mode || '').trim() || (s ? modeWhenSupported : 'degraded')
  const message =
    String(r.message || '').trim() ||
    (s ? '' : String(fallbackMessageWhenDegraded || '').trim() || '当前能力在本环境不可用，已降级/不可用。')
  return { supported: s, mode, message, degraded: s === false || mode === 'degraded' }
}
