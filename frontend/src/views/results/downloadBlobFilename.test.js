import { describe, expect, it } from 'vitest'
import { formatDownloadBlobFilename } from './downloadBlobFilename.js'

describe('formatDownloadBlobFilename', () => {
  it('成功：字符串文件名保持原样', () => {
    expect(formatDownloadBlobFilename('OpenSEM_apa_table.xlsx')).toBe('OpenSEM_apa_table.xlsx')
  })

  it('边界：非字符串输入按既有 DOMString 语义转字符串', () => {
    expect(formatDownloadBlobFilename(undefined)).toBe('undefined')
  })
})
