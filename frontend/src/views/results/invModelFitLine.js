export function buildInvModelFitLine({ name, models, toNum }) {
  const rows = Array.isArray(models) ? models : []
  const m = rows.find((x) => String(x?.model || '').trim() === String(name || '').trim()) || {}
  const fit = m?.fit && typeof m.fit === 'object' ? m.fit : {}
  const cfi = toNum(fit.cfi)
  const tli = toNum(fit.tli)
  const rmsea = toNum(fit.rmsea)
  const srmr = toNum(fit.srmr)
  const conv = m.converged
  const convText = conv === true ? '收敛' : conv === false ? '未收敛' : '未知'
  const fmt4 = (n) => (n === null ? 'NA' : Number(n).toFixed(4))
  return `${name}：CFI=${fmt4(cfi)}，TLI=${fmt4(tli)}，RMSEA=${fmt4(rmsea)}，SRMR=${fmt4(srmr)}（${convText}）`
}
