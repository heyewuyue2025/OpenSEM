import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useDialogStore } from './dialogStore'

describe('dialogStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('confirm resolves true when accept called', async () => {
    const dialogStore = useDialogStore()
    const pending = dialogStore.confirm({ title: '确认', message: '继续？' })

    expect(dialogStore.current?.message).toBe('继续？')
    dialogStore.accept()

    await expect(pending).resolves.toBe(true)
    expect(dialogStore.current).toBe(null)
  })

  it('confirm resolves false when cancel called', async () => {
    const dialogStore = useDialogStore()
    const pending = dialogStore.confirm({ title: '确认', message: '继续？' })

    dialogStore.cancel()

    await expect(pending).resolves.toBe(false)
    expect(dialogStore.current).toBe(null)
  })
})
