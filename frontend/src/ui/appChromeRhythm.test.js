import { describe, expect, it } from 'vitest'
import { APP_CHROME_PAD_X, resolveCoreOuterPad } from './appChromeRhythm'

describe('appChromeRhythm', () => {
  it('各档侧向 padding 有稳定 clamp（成功：结构不变）', () => {
    expect(APP_CHROME_PAD_X.desktop).toContain('clamp')
    expect(APP_CHROME_PAD_X.narrow).toContain('clamp')
    expect(APP_CHROME_PAD_X.tablet).toContain('clamp')
  })

  it('窄屏/小平板返回与顶栏同源的 pad（成功）', () => {
    expect(resolveCoreOuterPad({ isNarrow: true, isTablet: false })).toBe(
      APP_CHROME_PAD_X.narrow
    )
    expect(resolveCoreOuterPad({ isNarrow: false, isTablet: true })).toBe(
      APP_CHROME_PAD_X.tablet
    )
  })

  it('桌面不设 core 外沿覆盖（历史兜底/失败场景）', () => {
    expect(
      resolveCoreOuterPad({ isNarrow: false, isTablet: false })
    ).toBeNull()
    expect(resolveCoreOuterPad({})).toBeNull()
  })
})
