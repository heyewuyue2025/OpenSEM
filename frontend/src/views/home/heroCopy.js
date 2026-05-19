const DEFAULT_HERO_COPY = Object.freeze({
  eyebrow: 'STRUCTURAL EQUATION MODELING / 结构方程建模平台',
  quote: 'SEM，一条主线完成分析与导出',
  translation: 'Run SEM in one guided flow.',
  subtitle: '上传数据、表单建模、查看结果并导出报告，核心流程一步衔接一步。',
  assistive: '面向高校科研与实务分析，提供可解释、可追溯的结构方程建模体验。',
  cta: '立即开始',
})

const HERO_CTA_SYNONYMS = new Set(['开始分析', '马上开始', '立刻体验', '免费试试'])

function normalizeCopyField(value, fallback) {
  if (typeof value !== 'string') return fallback
  const trimmed = value.trim()
  return trimmed || fallback
}

function normalizeHeroCta(value) {
  if (typeof value !== 'string') {
    return DEFAULT_HERO_COPY.cta
  }
  const trimmed = value.trim()
  if (!trimmed) return DEFAULT_HERO_COPY.cta
  if (trimmed === DEFAULT_HERO_COPY.cta) return trimmed
  if (HERO_CTA_SYNONYMS.has(trimmed)) return DEFAULT_HERO_COPY.cta
  return trimmed
}

export function resolveHeroCopy(input) {
  if (!input || typeof input !== 'object') {
    return { ...DEFAULT_HERO_COPY }
  }

  return {
    eyebrow: normalizeCopyField(input.eyebrow, DEFAULT_HERO_COPY.eyebrow),
    quote: normalizeCopyField(input.quote, DEFAULT_HERO_COPY.quote),
    translation: normalizeCopyField(input.translation, DEFAULT_HERO_COPY.translation),
    subtitle: normalizeCopyField(input.subtitle, DEFAULT_HERO_COPY.subtitle),
    assistive: normalizeCopyField(input.assistive, DEFAULT_HERO_COPY.assistive),
    cta: normalizeHeroCta(input.cta),
  }
}
