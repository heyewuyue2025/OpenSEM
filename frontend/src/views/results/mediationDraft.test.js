import { describe, expect, it } from 'vitest'
import { parseMediatorChain } from './mediationDraft'

describe('parseMediatorChain', () => {
  it('应解析逗号分隔并去除空白', () => {
    expect(parseMediatorChain('M1, M2 ,M3')).toEqual(['M1', 'M2', 'M3'])
  })

  it('应过滤空项与多余分隔符', () => {
    expect(parseMediatorChain(' M1, , ,M2,')).toEqual(['M1', 'M2'])
  })

  it('空输入应返回空数组', () => {
    expect(parseMediatorChain(null)).toEqual([])
  })
})
