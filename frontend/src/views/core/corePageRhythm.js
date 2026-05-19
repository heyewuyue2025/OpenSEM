const DEFAULT_CORE_PAGE_RHYTHM = Object.freeze({
  sectionGap: '1.5rem',
  labelGap: '0.52rem',
  ruleGap: '0.95rem',
  introGap: '0.9rem',
  blockGap: '0.85rem',
})

/** 将节奏对象转为根节点可绑定的 CSS 变量（--osem-section-gap 等） */
export function toCorePageStyleVars(rhythm) {
  if (!rhythm || typeof rhythm !== 'object') return {}
  return {
    '--osem-section-gap': rhythm.sectionGap,
    '--osem-label-gap': rhythm.labelGap,
    '--osem-rule-gap': rhythm.ruleGap,
    '--osem-intro-gap': rhythm.introGap,
    '--osem-block-gap': rhythm.blockGap,
  }
}

const CORE_PAGE_RHYTHM = Object.freeze({
  data: Object.freeze({
    sectionGap: '1.55rem',
    labelGap: '0.54rem',
    ruleGap: '0.95rem',
    introGap: '0.82rem',
    blockGap: '0.82rem',
  }),
  model: Object.freeze({
    sectionGap: '1.45rem',
    labelGap: '0.52rem',
    ruleGap: '0.92rem',
    introGap: '0.78rem',
    blockGap: '0.8rem',
  }),
  results: Object.freeze({
    sectionGap: '1.4rem',
    labelGap: '0.5rem',
    ruleGap: '0.9rem',
    introGap: '0.76rem',
    blockGap: '0.78rem',
  }),
})

export function resolveCorePageRhythm(pageKey) {
  const normalized = String(pageKey || '')
    .trim()
    .toLowerCase()
  return CORE_PAGE_RHYTHM[normalized] || DEFAULT_CORE_PAGE_RHYTHM
}

