const DEFAULT_QUICK_START_RESPONSIVE = Object.freeze({
  tablet768: {
    summaryMaxWidth: '56ch',
    cardPadding: '1.25rem',
    visualHeight: '108px',
  },
  mobile375: {
    labelGap: '0.5rem',
    cardGap: '0.7rem',
    titleLineHeight: 1.3,
    summaryLineHeight: 1.62,
    summaryMaxWidth: '34ch',
    linkTopGap: '0.65rem',
    cardPadding: '1rem',
    visualHeight: '92px',
  },
})

function normalizeString(value, fallback) {
  if (typeof value !== 'string') {
    return fallback
  }
  const trimmed = value.trim()
  return trimmed || fallback
}

function normalizeNumber(value, fallback) {
  const n = Number(value)
  return Number.isFinite(n) ? n : fallback
}

export function resolveQuickStartResponsive(input) {
  if (!input || typeof input !== 'object') {
    return {
      tablet768: { ...DEFAULT_QUICK_START_RESPONSIVE.tablet768 },
      mobile375: { ...DEFAULT_QUICK_START_RESPONSIVE.mobile375 },
    }
  }

  const rawTablet = input.tablet768 && typeof input.tablet768 === 'object' ? input.tablet768 : {}
  const rawMobile = input.mobile375 && typeof input.mobile375 === 'object' ? input.mobile375 : {}

  return {
    tablet768: {
      summaryMaxWidth: normalizeString(
        rawTablet.summaryMaxWidth,
        DEFAULT_QUICK_START_RESPONSIVE.tablet768.summaryMaxWidth,
      ),
      cardPadding: normalizeString(
        rawTablet.cardPadding,
        DEFAULT_QUICK_START_RESPONSIVE.tablet768.cardPadding,
      ),
      visualHeight: normalizeString(
        rawTablet.visualHeight,
        DEFAULT_QUICK_START_RESPONSIVE.tablet768.visualHeight,
      ),
    },
    mobile375: {
      labelGap: normalizeString(
        rawMobile.labelGap,
        DEFAULT_QUICK_START_RESPONSIVE.mobile375.labelGap,
      ),
      cardGap: normalizeString(rawMobile.cardGap, DEFAULT_QUICK_START_RESPONSIVE.mobile375.cardGap),
      titleLineHeight: normalizeNumber(
        rawMobile.titleLineHeight,
        DEFAULT_QUICK_START_RESPONSIVE.mobile375.titleLineHeight,
      ),
      summaryLineHeight: normalizeNumber(
        rawMobile.summaryLineHeight,
        DEFAULT_QUICK_START_RESPONSIVE.mobile375.summaryLineHeight,
      ),
      summaryMaxWidth: normalizeString(
        rawMobile.summaryMaxWidth,
        DEFAULT_QUICK_START_RESPONSIVE.mobile375.summaryMaxWidth,
      ),
      linkTopGap: normalizeString(
        rawMobile.linkTopGap,
        DEFAULT_QUICK_START_RESPONSIVE.mobile375.linkTopGap,
      ),
      cardPadding: normalizeString(
        rawMobile.cardPadding,
        DEFAULT_QUICK_START_RESPONSIVE.mobile375.cardPadding,
      ),
      visualHeight: normalizeString(
        rawMobile.visualHeight,
        DEFAULT_QUICK_START_RESPONSIVE.mobile375.visualHeight,
      ),
    },
  }
}
