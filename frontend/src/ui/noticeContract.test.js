import { describe, it, expect } from 'vitest'
import { NOTICE, resolveNoticeTone } from './noticeContract.js'

describe('noticeContract', () => {
  it('notice 契约类名使用统一前缀', () => {
    expect(NOTICE.base).toMatch(/\bosem-notice\b/)
    expect(NOTICE.title).toMatch(/\bosem-notice__title\b/)
    expect(NOTICE.message).toMatch(/\bosem-notice__message\b/)
    expect(NOTICE.close).toMatch(/\bosem-notice__close\b/)
  })

  it('resolveNoticeTone：已支持语义返回对应 tone', () => {
    expect(resolveNoticeTone('warning')).toBe(NOTICE.toneWarning)
    expect(resolveNoticeTone('success')).toBe(NOTICE.toneSuccess)
    expect(resolveNoticeTone('info')).toBe(NOTICE.toneInfo)
  })

  it('resolveNoticeTone：未知语义回退 error（失败兜底）', () => {
    expect(resolveNoticeTone('unexpected')).toBe(NOTICE.toneError)
    expect(resolveNoticeTone()).toBe(NOTICE.toneError)
    expect(resolveNoticeTone('')).toBe(NOTICE.toneError)
  })
})
