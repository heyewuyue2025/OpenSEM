import { describe, expect, it } from 'vitest'
import { resolveHeroHierarchy } from './heroHierarchy'

describe('resolveHeroHierarchy', () => {
  it('空输入时返回首屏默认信息层级', () => {
    expect(resolveHeroHierarchy()).toEqual({
      eyebrow: 'STRUCTURAL EQUATION MODELING / 结构方程建模平台',
      quote: 'SEM，易如反掌',
      translation: 'SEM made effortless.',
      subtitle: '上传数据、完成建模、查看结果并导出报告，一条主线闭环完成。',
      assistive: '面向高校科研与实务分析的可解释建模工作流。',
    })
  })

  it('非法输入时回退默认层级（失败兜底）', () => {
    expect(resolveHeroHierarchy('bad-input')).toEqual({
      eyebrow: 'STRUCTURAL EQUATION MODELING / 结构方程建模平台',
      quote: 'SEM，易如反掌',
      translation: 'SEM made effortless.',
      subtitle: '上传数据、完成建模、查看结果并导出报告，一条主线闭环完成。',
      assistive: '面向高校科研与实务分析的可解释建模工作流。',
    })
  })
})
