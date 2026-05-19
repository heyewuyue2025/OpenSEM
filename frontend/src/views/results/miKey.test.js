import { describe, expect, it } from 'vitest'
import { miKey } from './miKey'

describe('miKey', () => {
  it('成功：lhs/op/rhs 拼接为稳定键', () => {
    expect(miKey({ lhs: 'F1', op: '=~', rhs: 'x3' })).toBe('F1::=~::x3')
    expect(miKey({ lhs: 'Y', op: '~', rhs: 'X' })).toBe('Y::~::X')
  })

  it('边界：空项或缺字段时为 ::::（与 ignoreMi 哨兵一致）', () => {
    expect(miKey(null)).toBe('::::')
    expect(miKey({})).toBe('::::')
    expect(miKey({ lhs: '', op: '', rhs: '' })).toBe('::::')
  })
})
