export function resolveModelCompareFeedback(state = {}) {
  if (state.modelCompareRunning) {
    return {
      kind: 'loading',
      text: '模型比较运行中…',
      detail: state.modelCompareTaskMessage || '请稍候，任务完成后将展示 AIC/BIC 与嵌套对比。',
    }
  }
  if (state.modelCompareError) {
    return {
      kind: 'error',
      text: state.modelCompareError,
      detail: state.modelCompareErrorHint || '请检查 Model B 语法与数据完整性后重试。',
    }
  }
  const n = Number(state.modelCompareModelsCount) || 0
  if (n > 0) {
    return {
      kind: 'success',
      text: `模型比较已完成（${n} 个模型）`,
      detail: '可继续查看拟合指数与 Δχ² 对比，并可通过导出携带对比结果。',
    }
  }
  return null
}
