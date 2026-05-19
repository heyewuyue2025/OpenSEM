import { BTN } from './buttonContract'

/**
 * 全局 dialog 的 class 契约（单一来源，便于回归与命名一致）
 */
export const DIALOG = Object.freeze({
  mask: 'osem-dialog__mask',
  panel: 'osem-dialog__panel',
  title: 'osem-dialog__title',
  message: 'osem-dialog__message',
  actions: 'osem-dialog__actions',
  cancel: `${BTN.secondaryMuted} osem-dialog__btn osem-dialog__btn--cancel`,
  confirm: `${BTN.primary} osem-dialog__btn osem-dialog__btn--confirm`,
})

/**
 * @param {string} [key]
 * @returns {string}
 */
export function pickDialogClass(key) {
  if (typeof key === 'string' && Object.prototype.hasOwnProperty.call(DIALOG, key)) {
    return DIALOG[key]
  }
  return DIALOG.panel
}
