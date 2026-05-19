import { describe, expect, it } from 'vitest'
import { resolveMgaFeedback } from './mgaFeedback'

describe('resolveMgaFeedback', () => {
  it('运行中时返回 loading 反馈', () => {
    const result = resolveMgaFeedback({
      mgaRunning: true,
      mgaTaskMessage: '队列中（40%）',
    })
    expect(result).toEqual({
      kind: 'loading',
      text: 'MGA 逐步比较运行中…',
      detail: '队列中（40%）',
    })
  })

  it('错误时返回 error 反馈（失败分支）', () => {
    const result = resolveMgaFeedback({
      mgaError: 'MGA 任务失败',
      mgaErrorHint: '某组模型未收敛',
    })
    expect(result).toEqual({
      kind: 'error',
      text: 'MGA 任务失败',
      detail: '某组模型未收敛',
    })
  })

  it('有结果块时返回 success 反馈', () => {
    const result = resolveMgaFeedback({ mgaItemsCount: 2 })
    expect(result).toEqual({
      kind: 'success',
      text: 'MGA 逐步比较已完成（2 条层级×路径结果）',
      detail: '可继续查看组别系数与 Δχ² 对比，并可通过导出携带 MGA 结果。',
    })
  })

  it('成功且带服务端 message 时合并 detail', () => {
    const result = resolveMgaFeedback({
      mgaItemsCount: 1,
      mgaResultMessage: '已按 lavaan 嵌套模型完成 LRT。',
    })
    expect(result?.kind).toBe('success')
    expect(result?.detail).toContain('已按 lavaan 嵌套模型完成 LRT。')
    expect(result?.detail).toContain('可继续查看组别系数')
  })

  it('无状态时返回 null（失败兜底）', () => {
    expect(resolveMgaFeedback({})).toBeNull()
    expect(resolveMgaFeedback({ mgaItemsCount: 0 })).toBeNull()
  })
})
