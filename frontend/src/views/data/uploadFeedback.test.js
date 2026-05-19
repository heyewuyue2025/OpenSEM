import { describe, expect, it } from 'vitest'
import { resolveUploadFeedback } from './uploadFeedback'

describe('resolveUploadFeedback', () => {
  it('在 loading 时返回统一加载反馈', () => {
    const result = resolveUploadFeedback({ loading: true, error: 'x' })
    expect(result).toEqual({
      kind: 'loading',
      text: '解析中…',
      detail: '请稍候，正在解析并校验数据格式。',
    })
  })

  it('在 error 时返回错误反馈', () => {
    const result = resolveUploadFeedback({ error: '文件解析失败' })
    expect(result).toEqual({
      kind: 'error',
      text: '文件解析失败',
      detail: '请检查文件格式或内容后重试上传。',
    })
  })

  it('在 parseMessage 时返回成功反馈', () => {
    const result = resolveUploadFeedback({ parseMessage: '解析成功，data_key=abc' })
    expect(result).toEqual({
      kind: 'success',
      text: '解析成功，data_key=abc',
      detail: '可继续到建模页进行下一步配置。',
    })
  })

  it('无状态时返回 null（失败兜底）', () => {
    expect(resolveUploadFeedback({})).toBeNull()
  })
})
