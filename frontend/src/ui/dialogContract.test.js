import { describe, it, expect } from 'vitest'
import { DIALOG, pickDialogClass } from './dialogContract.js'

describe('dialogContract', () => {
  it('dialog 契约类名使用统一前缀', () => {
    expect(DIALOG.mask).toMatch(/\bosem-dialog__mask\b/)
    expect(DIALOG.panel).toMatch(/\bosem-dialog__panel\b/)
    expect(DIALOG.title).toMatch(/\bosem-dialog__title\b/)
    expect(DIALOG.message).toMatch(/\bosem-dialog__message\b/)
    expect(DIALOG.actions).toMatch(/\bosem-dialog__actions\b/)
  })

  it('主次按钮继承按钮契约并附带 dialog 语义类', () => {
    expect(DIALOG.cancel).toMatch(/\bosem-btn\b/)
    expect(DIALOG.cancel).toMatch(/\bosem-dialog__btn--cancel\b/)
    expect(DIALOG.confirm).toMatch(/\bosem-btn\b/)
    expect(DIALOG.confirm).toMatch(/\bosem-dialog__btn--confirm\b/)
  })

  it('pickDialogClass：未知 key 回退 panel（失败兜底）', () => {
    expect(pickDialogClass('message')).toBe(DIALOG.message)
    expect(pickDialogClass('not-exists')).toBe(DIALOG.panel)
    expect(pickDialogClass()).toBe(DIALOG.panel)
  })
})
