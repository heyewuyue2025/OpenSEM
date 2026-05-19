import { resolveCorePageRhythm } from './corePageRhythm'

const NARROW = Object.freeze({
  data: Object.freeze({
    sectionGap: '1.2rem',
    labelGap: '0.48rem',
    ruleGap: '0.88rem',
    introGap: '0.7rem',
    blockGap: '0.7rem',
  }),
  model: Object.freeze({
    sectionGap: '1.12rem',
    labelGap: '0.46rem',
    ruleGap: '0.86rem',
    introGap: '0.68rem',
    blockGap: '0.68rem',
  }),
})

const TABLET = Object.freeze({
  data: Object.freeze({
    sectionGap: '1.4rem',
    labelGap: '0.51rem',
    ruleGap: '0.92rem',
    introGap: '0.78rem',
    blockGap: '0.78rem',
  }),
  model: Object.freeze({
    sectionGap: '1.32rem',
    labelGap: '0.5rem',
    ruleGap: '0.9rem',
    introGap: '0.75rem',
    blockGap: '0.76rem',
  }),
})

/**
 * Data / Model 在 375（窄屏）与 768–1023（小平板）下相对桌面基线收紧节奏，避免信息堆叠时层级塌陷。
 * 其它 pageKey 仅返回 `resolveCorePageRhythm` 基线（便于未来扩展、单测可断言无意外合并）。
 */
export function resolveCorePageRhythmForViewport(
  pageKey,
  { isNarrow, isTablet } = {}
) {
  const base = { ...resolveCorePageRhythm(pageKey) }
  const k = String(pageKey || '')
    .trim()
    .toLowerCase()
  if (k === 'data' && isNarrow) {
    return { ...base, ...NARROW.data }
  }
  if (k === 'model' && isNarrow) {
    return { ...base, ...NARROW.model }
  }
  if (k === 'data' && isTablet && !isNarrow) {
    return { ...base, ...TABLET.data }
  }
  if (k === 'model' && isTablet && !isNarrow) {
    return { ...base, ...TABLET.model }
  }
  return base
}
