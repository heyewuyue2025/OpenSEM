import { describe, expect, it } from 'vitest'
import { normalizeSyntaxForCompare } from './normalizeSyntaxForCompare'

describe('normalizeSyntaxForCompare', () => {
  it('规范化语法文本并移除空行', () => {
    const input = '  y ~ x  \n\n  m ~ x  \n'
    expect(normalizeSyntaxForCompare(input)).toBe('y ~ x\nm ~ x')
  })

  it('在无效输入时返回空字符串兜底', () => {
    expect(normalizeSyntaxForCompare(null)).toBe('')
  })
})
