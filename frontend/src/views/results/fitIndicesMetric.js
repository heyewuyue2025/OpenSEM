import { toNum } from './toNum'

/**
 * 拟合度指标展示值（与 Results FIT INDICES 区一致）。
 * @param {string} key
 * @param {Record<string, unknown> | null | undefined} fitIndices
 */
export function formatFitMetricValue(key, fitIndices) {
  const v = fitIndices?.[key]
  return v === null || v === undefined ? '—' : String(v)
}

/**
 * 拟合度指标一句话解释（与 Results FIT INDICES 区一致）。
 * @param {string} key
 * @param {Record<string, unknown> | null | undefined} fitIndices
 */
export function explainFitMetric(key, fitIndices) {
  const fit = fitIndices
  if (!fit) return '运行估算后解释会出现在这里'
  const v = toNum(fit[key])
  if (v === null) return '未能计算该指标（可能与样本/模型有关）'

  if (key === 'chi2_df') {
    if (v < 3) return `χ²/df=${v.toFixed(3)}，通常认为拟合较好`
    if (v <= 5) return `χ²/df=${v.toFixed(3)}，拟合偏临界，建议结合其他指标`
    return `χ²/df=${v.toFixed(3)}，偏高，可能存在模型设定问题`
  }
  if (key === 'rmsea') {
    if (v < 0.06) return `RMSEA=${v.toFixed(3)}，近似误差较小（较好）`
    if (v <= 0.1) return `RMSEA=${v.toFixed(3)}，处于可接受边界`
    return `RMSEA=${v.toFixed(3)}，偏高，建议回到建模页调整`
  }
  if (key === 'srmr') {
    if (v < 0.08) return `SRMR=${v.toFixed(3)}，残差整体较小（较好）`
    if (v <= 0.1) return `SRMR=${v.toFixed(3)}，临界，可尝试优化模型`
    return `SRMR=${v.toFixed(3)}，偏高，说明残差较大`
  }
  if (key === 'cfi') {
    if (v >= 0.95) return `CFI=${v.toFixed(3)}，比较拟合很好`
    if (v >= 0.9) return `CFI=${v.toFixed(3)}，通常视为可接受`
    return `CFI=${v.toFixed(3)}，略低于推荐阈值，建议参考修正方向`
  }
  if (key === 'tli') {
    if (v >= 0.95) return `TLI=${v.toFixed(3)}，较好`
    if (v >= 0.9) return `TLI=${v.toFixed(3)}，可接受`
    return `TLI=${v.toFixed(3)}，偏低，可能需要调整模型`
  }
  return '—'
}
