/**
 * MGA 结构路径跨组逐步比较：与 bootstrap/modelCompare/invarianceSeries 反馈块一致的状态解析。
 * @param {object} state
 * @param {boolean} [state.mgaRunning]
 * @param {string} [state.mgaTaskMessage]
 * @param {string} [state.mgaError]
 * @param {string} [state.mgaErrorHint]
 * @param {number} [state.mgaItemsCount] 与 ResultsView `mgaItems` 长度一致（层级×路径结果块数）
 * @param {string} [state.mgaResultMessage] 后端/任务返回的说明文案（可选，并入 success detail）
 */
export function resolveMgaFeedback(state = {}) {
  if (state.mgaRunning) {
    return {
      kind: 'loading',
      text: 'MGA 逐步比较运行中…',
      detail: state.mgaTaskMessage || '请稍候，任务完成后将展示层级×路径的组别系数与 LRT。',
    }
  }
  if (state.mgaError) {
    return {
      kind: 'error',
      text: state.mgaError,
      detail: state.mgaErrorHint || '请检查分组变量、已选结构路径与语法后重试。',
    }
  }
  const n = Number(state.mgaItemsCount) || 0
  if (n > 0) {
    const base = '可继续查看组别系数与 Δχ² 对比，并可通过导出携带 MGA 结果。'
    const msg = String(state.mgaResultMessage || '').trim()
    const detail = msg ? `${msg} ${base}` : base
    return {
      kind: 'success',
      text: `MGA 逐步比较已完成（${n} 条层级×路径结果）`,
      detail,
    }
  }
  return null
}
