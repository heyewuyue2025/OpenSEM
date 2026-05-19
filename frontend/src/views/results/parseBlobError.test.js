import { describe, expect, it } from 'vitest'
import { parseBlobError } from './parseBlobError.js'

describe('parseBlobError', () => {
  it('成功：可从 Blob JSON 的 detail 字符串提取错误信息', async () => {
    const error = {
      response: {
        data: new Blob([JSON.stringify({ detail: '导出失败：字段缺失' })], { type: 'application/json' }),
      },
    }
    await expect(parseBlobError(error, 'fallback')).resolves.toBe('导出失败：字段缺失')
  })

  it('边界：Blob 解析失败时回退到 error.message', async () => {
    const error = {
      message: 'network timeout',
      response: {
        data: new Blob(['not-json'], { type: 'application/json' }),
      },
    }
    await expect(parseBlobError(error, 'fallback')).resolves.toBe('network timeout')
  })

  it('边界：非 Blob detail.message 也可提取', async () => {
    const error = {
      response: {
        data: {
          detail: { message: 'docx 导出失败' },
        },
      },
    }
    await expect(parseBlobError(error, 'fallback')).resolves.toBe('docx 导出失败')
  })
})
