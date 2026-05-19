/**
 * 核心页按钮 class 契约（单一来源，便于回归与命名一致）
 */

export const BTN = Object.freeze({
  primary: 'osem-btn osem-btn--primary',
  secondary: 'osem-btn osem-btn--secondary',
  ghost: 'osem-btn osem-btn--ghost',
  secondaryAccent: 'osem-btn osem-btn--secondary-accent',
  secondaryMuted: 'osem-btn osem-btn--secondary-muted',
})

/**
 * @param {string} [key]
 * @returns {string}
 */
export function pickButtonVariant(key) {
  if (typeof key === 'string' && Object.prototype.hasOwnProperty.call(BTN, key)) {
    return BTN[key]
  }
  return BTN.secondary
}
