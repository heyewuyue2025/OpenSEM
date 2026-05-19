import { describe, expect, it, vi } from 'vitest'
import { pushErrorNotice, pushWarningNotice, requestUserConfirm } from './uiFeedback'

describe('uiFeedback', () => {
  it('pushErrorNotice pushes normalized error notice', () => {
    const push = vi.fn()
    const noticeStore = { push }

    pushErrorNotice(noticeStore, '缺失率 > 5%')

    expect(push).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'error',
        title: '错误提示',
        message: '缺失率 > 5%',
      })
    )
  })

  it('pushWarningNotice pushes warning notice', () => {
    const push = vi.fn()
    const noticeStore = { push }

    pushWarningNotice(noticeStore, '请先上传数据')

    expect(push).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'warning',
        title: '操作提醒',
        message: '请先上传数据',
      })
    )
  })

  it('requestUserConfirm proxies to dialog store confirm', async () => {
    const confirm = vi.fn().mockResolvedValue(true)
    const dialogStore = { confirm }

    const ok = await requestUserConfirm(dialogStore, {
      title: '确认操作',
      message: '继续吗？',
    })

    expect(ok).toBe(true)
    expect(confirm).toHaveBeenCalledWith(
      expect.objectContaining({
        title: '确认操作',
        message: '继续吗？',
      })
    )
  })
})
