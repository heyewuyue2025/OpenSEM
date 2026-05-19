export function fmt(v) {
  if (v === null || v === undefined) return '—'
  const n = Number(v)
  return Number.isFinite(n) ? String(n) : String(v)
}

export function fmtP(v) {
  if (v === null || v === undefined) return '—'
  const n = Number(v)
  if (!Number.isFinite(n)) return String(v)
  if (n < 0.001) return '<0.001'
  return String(n)
}

export function fmtCi(ci) {
  if (!ci) return '—'
  const lo = ci.lo
  const hi = ci.hi
  if (lo === null || lo === undefined || hi === null || hi === undefined) return '—'
  return `[${fmt(lo)}, ${fmt(hi)}]`
}
