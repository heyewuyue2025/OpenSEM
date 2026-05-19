const DEFAULT_ANALYSIS_OVERVIEW_COPY = Object.freeze({
  sectionLabel: 'ANALYSIS OVERVIEW / 分析概览',
  metrics: Object.freeze([
    Object.freeze({ key: 'sampleN', label: '样本量 Sample N' }),
    Object.freeze({ key: 'latent', label: '潜变量数量' }),
    Object.freeze({ key: 'cfi', label: '拟合指标 CFI' }),
  ]),
})

const ANALYSIS_OVERVIEW_LABEL_SYNONYMS = new Map([
  ['样本量 N', '样本量 Sample N'],
  ['潜变量 Latent', '潜变量数量'],
  ['拟合 CFI', '拟合指标 CFI'],
])

function normalizeText(value, fallback) {
  if (typeof value !== 'string') return fallback
  const trimmed = value.trim()
  return trimmed || fallback
}

function normalizeMetric(metric, fallback) {
  if (!metric || typeof metric !== 'object') {
    return { ...fallback }
  }
  const label = normalizeText(metric.label, fallback.label)
  return {
    key: fallback.key,
    label: ANALYSIS_OVERVIEW_LABEL_SYNONYMS.get(label) || label,
  }
}

export function resolveAnalysisOverviewCopy(input) {
  if (!input || typeof input !== 'object') {
    return {
      sectionLabel: DEFAULT_ANALYSIS_OVERVIEW_COPY.sectionLabel,
      metrics: DEFAULT_ANALYSIS_OVERVIEW_COPY.metrics.map((metric) => ({ ...metric })),
    }
  }

  const incomingMetrics = Array.isArray(input.metrics) ? input.metrics : []
  return {
    sectionLabel: normalizeText(input.sectionLabel, DEFAULT_ANALYSIS_OVERVIEW_COPY.sectionLabel),
    metrics: DEFAULT_ANALYSIS_OVERVIEW_COPY.metrics.map((fallbackMetric, idx) =>
      normalizeMetric(incomingMetrics[idx], fallbackMetric),
    ),
  }
}
