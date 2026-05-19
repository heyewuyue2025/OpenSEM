const DEFAULT_QUICK_START_COPY = Object.freeze({
  sectionLabel: 'QUICK START / 快速开始',
  title: '从零完成一次完整 SEM 分析',
  summary: '数据导入、CFA 建模、路径设定、拟合度解读、APA 表格导出。',
  cta: '立即开始',
})

export function resolveQuickStartCopy(input) {
  if (!input || typeof input !== 'object') {
    return { ...DEFAULT_QUICK_START_COPY }
  }

  const sectionLabel = typeof input.sectionLabel === 'string' ? input.sectionLabel.trim() : ''
  const title = typeof input.title === 'string' ? input.title.trim() : ''
  const summary = typeof input.summary === 'string' ? input.summary.trim() : ''
  const cta = typeof input.cta === 'string' ? input.cta.trim() : ''

  return {
    sectionLabel: sectionLabel || DEFAULT_QUICK_START_COPY.sectionLabel,
    title: title || DEFAULT_QUICK_START_COPY.title,
    summary: summary || DEFAULT_QUICK_START_COPY.summary,
    cta: cta || DEFAULT_QUICK_START_COPY.cta,
  }
}
