import { describe, expect, it } from 'vitest'
import { FEEDBACK, resolveFeedbackTone } from './feedbackContract'

describe('feedbackContract', () => {
  it('为 loading/success/error 返回统一状态类（成功路径）', () => {
    expect(resolveFeedbackTone('loading')).toBe('is-loading')
    expect(resolveFeedbackTone('success')).toBe('is-success')
    expect(resolveFeedbackTone('error')).toBe('is-error')
  })

  it('未知状态降级为 warning（失败兜底）', () => {
    expect(resolveFeedbackTone('unknown')).toBe('is-warning')
    expect(resolveFeedbackTone()).toBe('is-warning')
  })

  it('暴露统一反馈类名前缀', () => {
    expect(FEEDBACK.base).toBe('osem-feedback')
    expect(FEEDBACK.text).toBe('osem-feedback-text')
    expect(FEEDBACK.detail).toBe('osem-feedback-detail')
  })
})
