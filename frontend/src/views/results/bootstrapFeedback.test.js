import { describe, expect, it } from 'vitest'
import { resolveBootstrapFeedback } from './bootstrapFeedback'

describe('resolveBootstrapFeedback', () => {
  it('运行中时返回 loading 反馈', () => {
    const result = resolveBootstrapFeedback({
      bootstrapping: true,
      bootstrapTaskMessage: '正在抽样（40%）',
    })
    expect(result).toEqual({
      kind: 'loading',
      text: 'Bootstrap 运行中…',
      detail: '正在抽样（40%）',
    })
  })

  it('错误时返回 error 反馈（失败分支）', () => {
    const result = resolveBootstrapFeedback({
      bootstrapError: 'Bootstrap 失败',
      bootstrapErrorHint: '样本不足',
    })
    expect(result).toEqual({
      kind: 'error',
      text: 'Bootstrap 失败',
      detail: '样本不足',
    })
  })

  it('有结果时返回 success 反馈', () => {
    const result = resolveBootstrapFeedback({ bootstrapResultItemsCount: 3 })
    expect(result).toEqual({
      kind: 'success',
      text: 'Bootstrap 已完成（3 条效应）',
      detail: '可继续查看置信区间并决定是否导出结果。',
    })
  })

  it('无状态时返回 null（失败兜底）', () => {
    expect(resolveBootstrapFeedback({})).toBeNull()
  })
})
