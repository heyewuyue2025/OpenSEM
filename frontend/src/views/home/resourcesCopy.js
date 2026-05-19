const DEFAULT_RESOURCES_COPY = Object.freeze({
  sectionLabel: 'RESOURCES / 学习资源',
  links: Object.freeze([
    Object.freeze({
      href: 'https://apastyle.apa.org/style-grammar-guidelines/tables-figures',
      label: 'APA 7th 表格与图示规范',
    }),
    Object.freeze({
      href: 'https://lavaan.ugent.be/tutorial/syntax1.html',
      label: 'lavaan 语法快速参考',
    }),
  ]),
})

const RESOURCES_LABEL_SYNONYMS = new Map([
  ['APA 7th 格式说明', 'APA 7th 表格与图示规范'],
  ['lavaan 语法参考', 'lavaan 语法快速参考'],
])

function normalizeText(value, fallback) {
  if (typeof value !== 'string') return fallback
  const trimmed = value.trim()
  return trimmed || fallback
}

function normalizeLink(link, fallback) {
  if (!link || typeof link !== 'object') {
    return { ...fallback }
  }
  const label = normalizeText(link.label, fallback.label)
  return {
    href: fallback.href,
    label: RESOURCES_LABEL_SYNONYMS.get(label) || label,
  }
}

export function resolveResourcesCopy(input) {
  if (!input || typeof input !== 'object') {
    return {
      sectionLabel: DEFAULT_RESOURCES_COPY.sectionLabel,
      links: DEFAULT_RESOURCES_COPY.links.map((link) => ({ ...link })),
    }
  }

  const incomingLinks = Array.isArray(input.links) ? input.links : []
  return {
    sectionLabel: normalizeText(input.sectionLabel, DEFAULT_RESOURCES_COPY.sectionLabel),
    links: DEFAULT_RESOURCES_COPY.links.map((fallbackLink, idx) =>
      normalizeLink(incomingLinks[idx], fallbackLink),
    ),
  }
}
