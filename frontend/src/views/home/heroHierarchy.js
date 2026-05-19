const DEFAULT_HERO_HIERARCHY = Object.freeze({
  eyebrow: 'STRUCTURAL EQUATION MODELING / 结构方程建模平台',
  quote: 'SEM，易如反掌',
  translation: 'SEM made effortless.',
  subtitle: '上传数据、完成建模、查看结果并导出报告，一条主线闭环完成。',
  assistive: '面向高校科研与实务分析的可解释建模工作流。',
})

export function resolveHeroHierarchy(input) {
  if (!input || typeof input !== 'object') {
    return { ...DEFAULT_HERO_HIERARCHY }
  }

  const eyebrow = typeof input.eyebrow === 'string' ? input.eyebrow.trim() : ''
  const quote = typeof input.quote === 'string' ? input.quote.trim() : ''
  const translation = typeof input.translation === 'string' ? input.translation.trim() : ''
  const subtitle = typeof input.subtitle === 'string' ? input.subtitle.trim() : ''
  const assistive = typeof input.assistive === 'string' ? input.assistive.trim() : ''

  return {
    eyebrow: eyebrow || DEFAULT_HERO_HIERARCHY.eyebrow,
    quote: quote || DEFAULT_HERO_HIERARCHY.quote,
    translation: translation || DEFAULT_HERO_HIERARCHY.translation,
    subtitle: subtitle || DEFAULT_HERO_HIERARCHY.subtitle,
    assistive: assistive || DEFAULT_HERO_HIERARCHY.assistive,
  }
}
