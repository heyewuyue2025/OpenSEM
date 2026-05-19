import { describe, expect, it } from 'vitest'
import { resolveInvarianceSeriesFeedback } from './invarianceSeriesFeedback'

describe('resolveInvarianceSeriesFeedback', () => {
  it('运行中时返回 loading 反馈', () => {
    const result = resolveInvarianceSeriesFeedback({
      invarianceSeriesRunning: true,
      invarianceSeriesTaskMessage: '队列中（40%）',
    })
    expect(result).toEqual({
      kind: 'loading',
      text: '不变性序列运行中…',
      detail: '队列中（40%）',
    })
  })

  it('错误时返回 error 反馈（失败分支）', () => {
    const result = resolveInvarianceSeriesFeedback({
      invarianceSeriesError: '序列任务失败',
      invarianceSeriesErrorHint: '某步模型未收敛',
    })
    expect(result).toEqual({
      kind: 'error',
      text: '序列任务失败',
      detail: '某步模型未收敛',
    })
  })

  it('有序列模型结果时返回 success 反馈', () => {
    const result = resolveInvarianceSeriesFeedback({ invarianceSeriesModelsCount: 4 })
    expect(result).toEqual({
      kind: 'success',
      text: '不变性序列已完成（4 个层级模型）',
      detail: '可继续查看 Δχ²/ΔCFI 与结论卡片，并可通过导出携带序列结果。',
    })
  })

  it('无状态时返回 null（失败兜底）', () => {
    expect(resolveInvarianceSeriesFeedback({})).toBeNull()
    expect(resolveInvarianceSeriesFeedback({ invarianceSeriesModelsCount: 0 })).toBeNull()
  })
})
