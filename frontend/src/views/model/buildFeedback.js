export function resolveBuildFeedback(state = {}) {
  const items = []
  const warnings = Array.isArray(state.warnings) ? state.warnings.filter(Boolean) : []

  if (state.copyToast) {
    items.push({
      kind: 'success',
      text: state.copyToast,
      detail: '复制结果已写入剪贴板，可直接粘贴使用。',
    })
  }
  if (state.error) {
    items.push({
      kind: 'error',
      text: state.error,
      detail: '请修正表单或数据后重试校验/转译。',
    })
  }
  if (warnings.length > 0) {
    items.push({
      kind: 'warning',
      text: `警告 ${warnings.length} 条`,
      detail: warnings.join('；'),
    })
  }

  return items
}
