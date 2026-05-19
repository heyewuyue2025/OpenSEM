export const MAIN_NAV_ITEMS = Object.freeze([
  { to: '/', label: '首页 / HOME' },
  { to: '/data', label: '数据导入 / DATA' },
  { to: '/model', label: '表单建模 / MODEL' },
  { to: '/results', label: '结果与导出 / RESULTS' },
])

export function resolveMainNavItems() {
  return MAIN_NAV_ITEMS
}
