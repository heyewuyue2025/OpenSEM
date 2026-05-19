/**
 * 顶栏 / 次导航 / 全局 notice·dialog 与三核心页 `--osem-core-outer-pad` 的侧向节奏对齐源。
 * 与 `style.css` 中 `--osem-app-chrome-pad-x` 的数值需保持一致（见文件内 sync 注释）。
 */
export const APP_CHROME_PAD_X = Object.freeze({
  desktop: 'clamp(1.5rem, 3vw, 2.5rem)',
  narrow: 'clamp(0.85rem, 4.2vw, 1.2rem)',
  tablet: 'clamp(1.1rem, 2.2vw, 1.6rem)',
})

/**
 * @param {{ isNarrow?: boolean, isTablet?: boolean }} [viewport]
 * @returns {string | null} 桌面不设覆盖时返回 `null`（与历史 `useOsemCorePageStyle` 行为一致）
 */
export function resolveCoreOuterPad({ isNarrow, isTablet } = {}) {
  if (isNarrow) {
    return APP_CHROME_PAD_X.narrow
  }
  if (isTablet) {
    return APP_CHROME_PAD_X.tablet
  }
  return null
}
