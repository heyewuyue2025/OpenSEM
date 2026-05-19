import { describe, expect, it } from 'vitest'
import { BTN } from '../../ui/buttonContract'
import { resolveHeroCtas } from './heroCta'

describe('resolveHeroCtas', () => {
  it('空输入时返回首屏默认 CTA', () => {
    expect(resolveHeroCtas()).toEqual([
      {
        id: 'primary',
        label: '立即开始',
        to: '/data',
        variant: BTN.primary,
      },
      {
        id: 'secondary',
        label: '查看演示',
        to: '/results',
        variant: BTN.secondaryMuted,
      },
    ])
  })

  it('非法输入时回退到默认 CTA（失败兜底）', () => {
    expect(resolveHeroCtas('bad-input')).toEqual([
      {
        id: 'primary',
        label: '立即开始',
        to: '/data',
        variant: BTN.primary,
      },
      {
        id: 'secondary',
        label: '查看演示',
        to: '/results',
        variant: BTN.secondaryMuted,
      },
    ])
  })

  it('自定义输入时按契约映射 variant', () => {
    expect(
      resolveHeroCtas([
        { label: '主按钮', to: '/data', variantKey: 'primary' },
        { label: '次按钮', to: '/results', variantKey: 'secondaryMuted' },
      ]),
    ).toEqual([
      {
        id: 'cta-0',
        label: '主按钮',
        to: '/data',
        variant: BTN.primary,
      },
      {
        id: 'cta-1',
        label: '次按钮',
        to: '/results',
        variant: BTN.secondaryMuted,
      },
    ])
  })
})
