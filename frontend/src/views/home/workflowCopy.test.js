import { describe, expect, it } from 'vitest'
import { resolveWorkflowCopy } from './workflowCopy'

describe('resolveWorkflowCopy', () => {
  it('空输入时返回 workflow 词典默认文案', () => {
    expect(resolveWorkflowCopy()).toEqual({
      sectionLabel: 'WORKFLOW / 分析流程',
      steps: [
        { path: '/data', title: '数据管理', desc: '数据导入 · 变量预览' },
        { path: '/model', title: '表单建模', desc: 'CFA 建模 · 路径设定 · 误差协变' },
        { path: '/results', title: '结果与导出', desc: '拟合度解读 · APA 表格导出' },
      ],
    })
  })

  it('将历史同义术语收敛到 workflow 词典口径（失败兜底）', () => {
    const copy = resolveWorkflowCopy({
      steps: [
        { path: '/data', desc: '导入 · 变量预览' },
        { path: '/model', desc: 'CFA · 路径 · 误差协变' },
        { path: '/results', desc: '拟合度 · APA 表格' },
      ],
    })
    expect(copy.steps).toEqual([
      { path: '/data', title: '数据管理', desc: '数据导入 · 变量预览' },
      { path: '/model', title: '表单建模', desc: 'CFA 建模 · 路径设定 · 误差协变' },
      { path: '/results', title: '结果与导出', desc: '拟合度解读 · APA 表格导出' },
    ])
  })
})
