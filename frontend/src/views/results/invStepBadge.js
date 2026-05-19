import { toNum } from './toNum.js'

const CFI_TH = 0.01
const RMSEA_TH = 0.015

/**
 * 不变性序列单步比较（configural→metric 等）的 PASS/FAIL 徽章与说明。
 * 与 Results 内原 `invStepBadge` 语义一致；`degraded` 须由调用方传入（对应 lavaan 降级等）。
 */
export function computeInvStepBadge(c, { degraded = false } = {}) {
  if (degraded) {
    return { badge: '—', status: 'unknown', note: '不可比：当前为降级结果（未启用 lavaan / LRT 不可用）' }
  }

  const note = String(c?.note || '').trim()
  const dcfi = toNum(c?.delta_cfi)
  const drmsea = toNum(c?.delta_rmsea)
  const has = dcfi !== null && drmsea !== null

  if (!has) {
    if (note) return { badge: '—', status: 'unknown', note: `不可比：${note}` }
    const missing = []
    if (dcfi === null) missing.push('ΔCFI')
    if (drmsea === null) missing.push('ΔRMSEA')
    return { badge: '—', status: 'unknown', note: `不可比：缺少 ${missing.join('/')}（可能未收敛或 lavTestLRT 不可用）` }
  }

  const ok = Math.abs(dcfi) < CFI_TH && Math.abs(drmsea) < RMSEA_TH
  const badge = ok ? 'PASS' : 'FAIL'
  const detail = `|ΔCFI|=${Math.abs(dcfi).toFixed(4)}，|ΔRMSEA|=${Math.abs(drmsea).toFixed(4)}`
  const finalNote = note ? `${detail}；${note}` : detail
  return { badge, status: ok ? 'pass' : 'fail', note: finalNote }
}
