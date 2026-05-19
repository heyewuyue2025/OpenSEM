import { describe, expect, it } from 'vitest'
import { normalizeMgaRows } from './normalizeMgaRows'

describe('normalizeMgaRows', () => {
  it('成功：扁平 estimate/std_all/p_value 行按组汇总', () => {
    const rows = normalizeMgaRows([
      { group: 'G1', estimate: 0.12, std_all: 0.34, p_value: 0.05, note: 'ok' },
      { group: 'G2', estimate: null, std_all: undefined, p_value: 0.01 },
    ])
    expect(rows).toHaveLength(2)
    expect(rows[0]).toEqual({
      group: 'G1',
      estimate: 0.12,
      std_all: 0.34,
      p_value: 0.05,
      note: 'ok',
    })
    expect(rows[1]).toEqual({
      group: 'G2',
      estimate: null,
      std_all: null,
      p_value: 0.01,
      note: '',
    })
  })

  it('边界：非数组或空输入返回空数组', () => {
    expect(normalizeMgaRows(null)).toEqual([])
    expect(normalizeMgaRows(undefined)).toEqual([])
    expect(normalizeMgaRows([])).toEqual([])
  })

  it('失败/嵌套：coef 分支与拟合失败文案', () => {
    expect(
      normalizeMgaRows([
        null,
        {
          group: 'A',
          success: false,
          error: '不收敛',
          coef: { estimate: 1, std_all: 2, p_value: 3 },
        },
        { group: 'B', coef: {} },
      ])
    ).toEqual([
      {
        group: 'A',
        estimate: 1,
        std_all: 2,
        p_value: 3,
        note: '不收敛',
      },
      {
        group: 'B',
        estimate: null,
        std_all: null,
        p_value: null,
        note: '',
      },
    ])
  })
})
