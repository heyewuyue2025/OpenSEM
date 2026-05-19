import { describe, expect, it } from 'vitest'
import { MAIN_NAV_ITEMS, resolveMainNavItems } from './navContract'

describe('navContract', () => {
  it('返回主导航统一口径（成功路径）', () => {
    expect(resolveMainNavItems()).toEqual([
      { to: '/', label: '首页 / HOME' },
      { to: '/data', label: '数据导入 / DATA' },
      { to: '/model', label: '表单建模 / MODEL' },
      { to: '/results', label: '结果与导出 / RESULTS' },
    ])
  })

  it('导航项顺序固定（失败兜底）', () => {
    expect(MAIN_NAV_ITEMS.map((item) => item.to)).toEqual(['/', '/data', '/model', '/results'])
  })
})
