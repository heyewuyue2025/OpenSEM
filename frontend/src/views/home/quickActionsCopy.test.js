import { describe, expect, it } from 'vitest'
import { resolveQuickActionsCopy } from './quickActionsCopy'

describe('resolveQuickActionsCopy', () => {
  it('空输入时返回 QUICK ACTIONS 默认词典', () => {
    expect(resolveQuickActionsCopy()).toEqual({
      sectionLabel: 'QUICK ACTIONS / 快捷入口',
      actions: [
        { to: '/data', label: '数据导入' },
        { to: '/model', label: '表单建模' },
        { to: '/results', label: '结果导出' },
      ],
    })
  })

  it('将历史同义词收敛到 QUICK ACTIONS 词典口径（失败兜底）', () => {
    const copy = resolveQuickActionsCopy({
      actions: [
        { to: '/data', label: '上传数据' },
        { to: '/model', label: '新建模型' },
        { to: '/results', label: '导出结果' },
      ],
    })

    expect(copy.actions).toEqual([
      { to: '/data', label: '数据导入' },
      { to: '/model', label: '表单建模' },
      { to: '/results', label: '结果导出' },
    ])
  })
})
