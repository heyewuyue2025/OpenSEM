import { describe, expect, it } from 'vitest'
import { resolveCorePageRhythm } from './corePageRhythm'
import { resolveCorePageRhythmForViewport } from './corePageViewportRhythm'

describe('resolveCorePageRhythmForViewport', () => {
  it('Data 页窄屏收紧节奏（成功场景）', () => {
    const v = { isNarrow: true, isTablet: false }
    expect(resolveCorePageRhythmForViewport('data', v).sectionGap).toBe('1.2rem')
  })

  it('Model 页小平板在桌面与窄屏之间（成功场景）', () => {
    const v = { isNarrow: false, isTablet: true }
    expect(resolveCorePageRhythmForViewport('model', v).sectionGap).toBe('1.32rem')
  })

  it('非 data/model 或桌面视口不合并窄屏/平板覆盖（失败兜底/隔离）', () => {
    const v = { isNarrow: true, isTablet: false }
    expect(resolveCorePageRhythmForViewport('results', v)).toEqual(resolveCorePageRhythm('results'))
  })
})
