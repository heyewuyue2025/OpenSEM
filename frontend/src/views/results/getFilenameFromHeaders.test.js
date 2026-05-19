import { describe, expect, it } from 'vitest'
import { getFilenameFromHeaders } from './getFilenameFromHeaders.js'

describe('getFilenameFromHeaders', () => {
  it('成功：优先解析 UTF-8 filename* 并解码', () => {
    const filename = getFilenameFromHeaders(
      { 'content-disposition': "attachment; filename*=UTF-8''OpenSEM_%E6%8A%A5%E5%91%8A.xlsx" },
      'fallback.xlsx'
    )
    expect(filename).toBe('OpenSEM_报告.xlsx')
  })

  it('边界：无 content-disposition 时回退 fallback', () => {
    const filename = getFilenameFromHeaders({}, 'fallback.xlsx')
    expect(filename).toBe('fallback.xlsx')
  })

  it('边界：UTF-8 编码非法时回退普通 filename', () => {
    const filename = getFilenameFromHeaders(
      { 'Content-Disposition': `attachment; filename*=UTF-8''%E0%A4%A; filename="plain.xlsx"` },
      'fallback.xlsx'
    )
    expect(filename).toBe('plain.xlsx')
  })
})
