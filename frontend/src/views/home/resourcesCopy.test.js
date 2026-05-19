import { describe, expect, it } from 'vitest'
import { resolveResourcesCopy } from './resourcesCopy'

describe('resolveResourcesCopy', () => {
  it('空输入时返回 RESOURCES 默认词典', () => {
    expect(resolveResourcesCopy()).toEqual({
      sectionLabel: 'RESOURCES / 学习资源',
      links: [
        {
          href: 'https://apastyle.apa.org/style-grammar-guidelines/tables-figures',
          label: 'APA 7th 表格与图示规范',
        },
        {
          href: 'https://lavaan.ugent.be/tutorial/syntax1.html',
          label: 'lavaan 语法快速参考',
        },
      ],
    })
  })

  it('将历史同义文案收敛为 RESOURCES 词典口径（失败兜底）', () => {
    const copy = resolveResourcesCopy({
      links: [
        { href: 'https://apastyle.apa.org/style-grammar-guidelines/tables-figures', label: 'APA 7th 格式说明' },
        { href: 'https://lavaan.ugent.be/tutorial/syntax1.html', label: 'lavaan 语法参考' },
      ],
    })

    expect(copy.links).toEqual([
      {
        href: 'https://apastyle.apa.org/style-grammar-guidelines/tables-figures',
        label: 'APA 7th 表格与图示规范',
      },
      {
        href: 'https://lavaan.ugent.be/tutorial/syntax1.html',
        label: 'lavaan 语法快速参考',
      },
    ])
  })
})
