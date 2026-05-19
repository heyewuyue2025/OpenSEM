import { describe, expect, it } from 'vitest'
import { resolveCorePageRhythm, toCorePageStyleVars } from './corePageRhythm'

describe('resolveCorePageRhythm', () => {
  it('返回 Results 页默认节奏参数（成功场景）', () => {
    expect(resolveCorePageRhythm('results')).toEqual({
      sectionGap: '1.4rem',
      labelGap: '0.5rem',
      ruleGap: '0.9rem',
      introGap: '0.76rem',
      blockGap: '0.78rem',
    })
  })

  it('未知页面键时回退通用节奏参数（失败兜底）', () => {
    expect(resolveCorePageRhythm('unknown-view')).toEqual({
      sectionGap: '1.5rem',
      labelGap: '0.52rem',
      ruleGap: '0.95rem',
      introGap: '0.9rem',
      blockGap: '0.85rem',
    })
  })
})

describe('toCorePageStyleVars', () => {
  it('将节奏对象转为 --osem-* 变量名（成功场景）', () => {
    expect(toCorePageStyleVars(resolveCorePageRhythm('data'))).toEqual({
      '--osem-section-gap': '1.55rem',
      '--osem-label-gap': '0.54rem',
      '--osem-rule-gap': '0.95rem',
      '--osem-intro-gap': '0.82rem',
      '--osem-block-gap': '0.82rem',
    })
  })

  it('非对象时返回空（失败兜底）', () => {
    expect(toCorePageStyleVars(null)).toEqual({})
  })
})

