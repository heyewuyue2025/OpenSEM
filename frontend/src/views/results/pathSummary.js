import { toNum } from './toNum'

export function buildPathSummaryRows(estimates) {
  const est = Array.isArray(estimates) ? estimates : []
  const rows = []
  for (const r of est) {
    if (!r || typeof r !== 'object') continue
    const op = String(r.op || '').trim()
    if (op !== '~') continue
    const outcome = String(r.lval || '').trim()
    const predictor = String(r.rval || '').trim()
    if (!outcome || !predictor) continue
    const p = toNum(r.p_value)
    if (p === null) continue
    const beta = toNum(r.est_std) ?? toNum(r.estimate)
    const significant = p < 0.05
    const direction = beta === null ? 'unknown' : beta > 0 ? 'positive' : beta < 0 ? 'negative' : 'zero'
    rows.push({
      predictor,
      outcome,
      op,
      beta,
      p_value: p,
      significant,
      direction,
      note: '',
    })
  }
  const abs = (x) => (x === null ? -1 : Math.abs(Number(x)))
  rows.sort((a, b) => {
    if (a.significant !== b.significant) return a.significant ? -1 : 1
    return abs(b.beta) - abs(a.beta)
  })
  return rows.slice(0, 80)
}

export function buildPathSummaryReportText({ estimates, nUsed }) {
  const rows = buildPathSummaryRows(estimates)
  const sig = rows.filter((r) => r.significant)
  const n = Number(nUsed || 0)
  const top = sig.slice(0, 6)
  const fmtBeta = (v) => (v === null ? 'NA' : Number(v).toFixed(3))
  const fmtP2 = (v) => (v === null ? 'NA' : Number(v) < 0.001 ? '<0.001' : String(v))
  const lines = []
  lines.push('【结构路径显著性汇总（可复制）】')
  if (n) lines.push(`样本量：N=${n}（按当前缺失处理策略）。`)
  lines.push("本段落仅汇总结构回归路径（op='~'），β 优先使用标准化估计（Est. Std），显著性门槛 p<0.05。")
  if (!rows.length) {
    lines.push("未在参数表中识别到可汇总的结构回归路径（可能为纯测量模型，或缺少 p 值）。")
    return lines.join('\n')
  }
  lines.push(`共识别到结构回归路径 ${rows.length} 条，其中显著 ${sig.length} 条。`)
  if (!sig.length) {
    lines.push('在 p<0.05 的门槛下，当前模型未观察到显著的结构回归路径。')
    return lines.join('\n')
  }
  lines.push('显著路径（按 |β| 由高到低，最多列出 6 条）：')
  for (const r of top) {
    lines.push(`${r.predictor} → ${r.outcome}（β=${fmtBeta(r.beta)}，p=${fmtP2(r.p_value)}）`)
  }
  if (sig.length > top.length) lines.push(`（其余 ${sig.length - top.length} 条显著路径已在下方汇总表中列出）`)
  return lines.join('\n')
}
