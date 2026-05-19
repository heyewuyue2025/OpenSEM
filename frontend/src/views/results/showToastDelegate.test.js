import { describe, expect, it, vi } from 'vitest'
import { delegateShowToast } from './showToastDelegate.js'

describe('delegateShowToast', () => {
  it('成功：先写入消息并重置定时器', () => {
    const setMessage = vi.fn()
    const clearTimer = vi.fn()
    const scheduled = vi.fn()
    const setTimer = vi.fn((value) => {
      if (typeof value === 'function') scheduled.mockImplementation(value)
    })

    delegateShowToast({
      msg: '已导出 APA .xlsx',
      clearTimer,
      setTimer,
      setMessage,
    })

    expect(setMessage).toHaveBeenNthCalledWith(1, '已导出 APA .xlsx')
    expect(clearTimer).toHaveBeenCalledTimes(1)
    expect(setTimer).toHaveBeenCalledTimes(1)
    expect(typeof setTimer.mock.calls[0][0]).toBe('function')
    expect(setTimer.mock.calls[0][1]).toBe(2200)
  })

  it('边界：支持空消息并在回调中清空状态', () => {
    vi.useFakeTimers()
    const setMessage = vi.fn()
    const clearTimer = vi.fn()
    let timerFn = null
    const setTimer = vi.fn((value) => {
      if (typeof value === 'function') timerFn = value
    })

    delegateShowToast({
      msg: '',
      clearTimer,
      setTimer,
      setMessage,
      duration: 10,
    })

    expect(setMessage).toHaveBeenNthCalledWith(1, '')
    expect(clearTimer).toHaveBeenCalledTimes(1)
    expect(typeof timerFn).toBe('function')

    timerFn()
    expect(setMessage).toHaveBeenNthCalledWith(2, '')
    expect(setTimer).toHaveBeenLastCalledWith(null)
    vi.useRealTimers()
  })
})
