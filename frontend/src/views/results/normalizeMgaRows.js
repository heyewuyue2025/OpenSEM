/**
 * 将 MGA 分组路径估计（扁平或嵌套 coef）归一为表格行结构（与 Results MGA 表一致）。
 * @param {unknown} groupEstimates
 * @returns {Array<{ group: string, estimate: unknown, std_all: unknown, p_value: unknown, note: string }>}
 */
export function normalizeMgaRows(groupEstimates) {
  const items = Array.isArray(groupEstimates) ? groupEstimates : []
  const out = []
  for (const it of items) {
    if (!it || typeof it !== 'object') continue
    if (it.estimate !== undefined || it.std_all !== undefined || it.p_value !== undefined) {
      out.push({
        group: it.group ?? '—',
        estimate: it.estimate ?? null,
        std_all: it.std_all ?? null,
        p_value: it.p_value ?? null,
        note: it.note ?? '',
      })
      continue
    }
    const coef = it.coef || {}
    out.push({
      group: it.group ?? '—',
      estimate: coef.estimate ?? null,
      std_all: coef.std_all ?? null,
      p_value: coef.p_value ?? null,
      note: it.success === false ? (it.error || '该组拟合失败') : coef ? '' : '未提取到该路径系数',
    })
  }
  return out
}
