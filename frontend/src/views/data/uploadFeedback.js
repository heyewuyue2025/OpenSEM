export function resolveUploadFeedback(state = {}) {
  if (state.loading) {
    return { kind: 'loading', text: '解析中…', detail: '请稍候，正在解析并校验数据格式。' }
  }
  if (state.error) {
    return { kind: 'error', text: state.error, detail: '请检查文件格式或内容后重试上传。' }
  }
  if (state.sessionInvalidWarning) {
    return { kind: 'warning', text: state.sessionInvalidWarning, detail: '数据会话已失效，请重新上传文件。' }
  }
  if (state.parseMessage) {
    return { kind: 'success', text: state.parseMessage, detail: '可继续到建模页进行下一步配置。' }
  }
  return null
}
