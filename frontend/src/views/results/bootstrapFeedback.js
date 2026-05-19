export function resolveBootstrapFeedback(state = {}) {
  if (state.bootstrapping) {
    return {
      kind: 'loading',
      text: 'Bootstrap 运行中…',
      detail: state.bootstrapTaskMessage || '请稍候，任务完成后将自动刷新结果。',
    }
  }
  if (state.bootstrapError) {
    return {
      kind: 'error',
      text: state.bootstrapError,
      detail: state.bootstrapErrorHint || '请检查路径配置与数据完整性后重试。',
    }
  }
  if (state.bootstrapResultItemsCount > 0) {
    return {
      kind: 'success',
      text: `Bootstrap 已完成（${state.bootstrapResultItemsCount} 条效应）`,
      detail: '可继续查看置信区间并决定是否导出结果。',
    }
  }
  return null
}
