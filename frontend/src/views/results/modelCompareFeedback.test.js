import { describe, expect, it } from 'vitest'
import { resolveModelCompareFeedback } from './modelCompareFeedback'

describe('resolveModelCompareFeedback', () => {
  it('运行中时返回 loading 反馈', () => {
    const result = resolveModelCompareFeedback({
      modelCompareRunning: true,
      modelCompareTaskMessage: '队列中（30%）',
    })
    expect(result).toEqual({
      kind: 'loading',
      text: '模型比较运行中…',
      detail: '队列中（30%）',
    })
  })

  it('错误时返回 error 反馈（失败分支）', () => {
    const result = resolveModelCompareFeedback({
      modelCompareError: '模型比较失败',
      modelCompareErrorHint: 'Model B 无法拟合',
    })
    expect(result).toEqual({
      kind: 'error',
      text: '模型比较失败',
      detail: 'Model B 无法拟合',
    })
  })

  it('有对比结果时返回 success 反馈', () => {
    const result = resolveModelCompareFeedback({ modelCompareModelsCount: 2 })
    expect(result).toEqual({
      kind: 'success',
      text: '模型比较已完成（2 个模型）',
      detail: '可继续查看拟合指数与 Δχ² 对比，并可通过导出携带对比结果。',
    })
  })

  it('无状态时返回 null（失败兜底）', () => {
    expect(resolveModelCompareFeedback({})).toBeNull()
    expect(resolveModelCompareFeedback({ modelCompareModelsCount: 0 })).toBeNull()
  })
})
