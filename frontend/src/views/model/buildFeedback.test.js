import { describe, expect, it } from 'vitest'
import { resolveBuildFeedback } from './buildFeedback'

describe('resolveBuildFeedback', () => {
  it('复制成功时返回 success 反馈', () => {
    const result = resolveBuildFeedback({ copyToast: '已复制 lavaan 语法' })
    expect(result).toEqual([
      {
        kind: 'success',
        text: '已复制 lavaan 语法',
        detail: '复制结果已写入剪贴板，可直接粘贴使用。',
      },
    ])
  })

  it('错误和警告同时存在时都应返回', () => {
    const result = resolveBuildFeedback({
      error: '模型不可识别',
      warnings: ['路径冲突', '样本量偏低'],
    })
    expect(result).toEqual([
      {
        kind: 'error',
        text: '模型不可识别',
        detail: '请修正表单或数据后重试校验/转译。',
      },
      {
        kind: 'warning',
        text: '警告 2 条',
        detail: '路径冲突；样本量偏低',
      },
    ])
  })

  it('空 warnings 自动兜底为空数组', () => {
    expect(resolveBuildFeedback({ warnings: null })).toEqual([])
  })

  it('无状态时返回空数组（失败兜底）', () => {
    expect(resolveBuildFeedback({})).toEqual([])
  })
})
