import { describe, expect, it, vi } from 'vitest'
import { delegateDownloadBlob } from './downloadBlobDelegate.js'

describe('delegateDownloadBlob', () => {
  it('成功：按既有顺序触发下载并回收对象 URL', () => {
    const createObjectURL = vi.fn(() => 'blob:demo')
    const revokeObjectURL = vi.fn()
    const click = vi.fn()
    const remove = vi.fn()
    const anchor = { href: '', download: '', click, remove }
    const createAnchor = vi.fn(() => anchor)
    const appendToBody = vi.fn()

    delegateDownloadBlob({
      blob: new Blob(['demo']),
      filename: 'OpenSEM_apa_table.xlsx',
      createObjectURL,
      revokeObjectURL,
      createAnchor,
      appendToBody,
    })

    expect(createObjectURL).toHaveBeenCalledTimes(1)
    expect(createAnchor).toHaveBeenCalledTimes(1)
    expect(anchor.href).toBe('blob:demo')
    expect(anchor.download).toBe('OpenSEM_apa_table.xlsx')
    expect(appendToBody).toHaveBeenCalledWith(anchor)
    expect(click).toHaveBeenCalledTimes(1)
    expect(remove).toHaveBeenCalledTimes(1)
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:demo')
  })

  it('边界：当锚点无 remove 方法时仍可正常回收 URL', () => {
    const createObjectURL = vi.fn(() => 'blob:edge')
    const revokeObjectURL = vi.fn()
    const click = vi.fn()
    const anchor = { href: '', download: '', click }
    const createAnchor = vi.fn(() => anchor)
    const appendToBody = vi.fn()

    delegateDownloadBlob({
      blob: new Blob(['edge']),
      filename: 'OpenSEM_model.lavaan.txt',
      createObjectURL,
      revokeObjectURL,
      createAnchor,
      appendToBody,
    })

    expect(click).toHaveBeenCalledTimes(1)
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:edge')
  })
})
