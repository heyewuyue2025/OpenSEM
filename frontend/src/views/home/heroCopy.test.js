import { describe, expect, it } from 'vitest'
import { resolveHeroCopy } from './heroCopy'

describe('resolveHeroCopy', () => {
  it('空输入时返回 Hero 词典默认文案', () => {
    expect(resolveHeroCopy()).toEqual({
      eyebrow: 'STRUCTURAL EQUATION MODELING / 结构方程建模平台',
      quote: 'SEM，一条主线完成分析与导出',
      translation: 'Run SEM in one guided flow.',
      subtitle: '上传数据、表单建模、查看结果并导出报告，核心流程一步衔接一步。',
      assistive: '面向高校科研与实务分析，提供可解释、可追溯的结构方程建模体验。',
      cta: '立即开始',
    })
  })

  it('支持将旧口径 CTA 同义词收敛为“立即开始”（失败兜底）', () => {
    expect(resolveHeroCopy({ cta: '开始分析' }).cta).toBe('立即开始')
    expect(resolveHeroCopy({ cta: '马上开始' }).cta).toBe('立即开始')
    expect(resolveHeroCopy({ cta: '立刻体验' }).cta).toBe('立即开始')
  })
})
