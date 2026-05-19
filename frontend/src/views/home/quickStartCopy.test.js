import { describe, expect, it } from 'vitest'
import { resolveQuickStartCopy } from './quickStartCopy'

describe('resolveQuickStartCopy', () => {
  it('空输入时返回 QUICK START 默认文案词典', () => {
    expect(resolveQuickStartCopy()).toEqual({
      sectionLabel: 'QUICK START / 快速开始',
      title: '从零完成一次完整 SEM 分析',
      summary: '数据导入、CFA 建模、路径设定、拟合度解读、APA 表格导出。',
      cta: '立即开始',
    })
  })

  it('非法输入时回退默认文案词典（失败兜底）', () => {
    expect(resolveQuickStartCopy('bad-input')).toEqual({
      sectionLabel: 'QUICK START / 快速开始',
      title: '从零完成一次完整 SEM 分析',
      summary: '数据导入、CFA 建模、路径设定、拟合度解读、APA 表格导出。',
      cta: '立即开始',
    })
  })
})
