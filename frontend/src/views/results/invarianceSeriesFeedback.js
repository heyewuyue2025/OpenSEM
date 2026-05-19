export function resolveInvarianceSeriesFeedback(state = {}) {
  if (state.invarianceSeriesRunning) {
    return {
      kind: 'loading',
      text: '不变性序列运行中…',
      detail: state.invarianceSeriesTaskMessage || '请稍候，任务完成后将展示各级模型与 LRT 对比。',
    }
  }
  if (state.invarianceSeriesError) {
    return {
      kind: 'error',
      text: state.invarianceSeriesError,
      detail: state.invarianceSeriesErrorHint || '请检查分组变量与语法后重试。',
    }
  }
  const n = Number(state.invarianceSeriesModelsCount) || 0
  if (n > 0) {
    return {
      kind: 'success',
      text: `不变性序列已完成（${n} 个层级模型）`,
      detail: '可继续查看 Δχ²/ΔCFI 与结论卡片，并可通过导出携带序列结果。',
    }
  }
  return null
}
