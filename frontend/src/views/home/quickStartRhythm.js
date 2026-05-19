const DEFAULT_QUICK_START_RHYTHM = Object.freeze({
  labelGap: '0.65rem',
  cardGap: '0.9rem',
  titleLineHeight: 1.35,
  summaryLineHeight: 1.7,
  summaryMaxWidth: '62ch',
  linkTopGap: '0.9rem',
})

export function resolveQuickStartRhythm(input) {
  if (!input || typeof input !== 'object') {
    return { ...DEFAULT_QUICK_START_RHYTHM }
  }

  const titleLineHeight = Number(input.titleLineHeight)
  const summaryLineHeight = Number(input.summaryLineHeight)
  const labelGap = typeof input.labelGap === 'string' ? input.labelGap.trim() : ''
  const cardGap = typeof input.cardGap === 'string' ? input.cardGap.trim() : ''
  const summaryMaxWidth =
    typeof input.summaryMaxWidth === 'string' ? input.summaryMaxWidth.trim() : ''
  const linkTopGap = typeof input.linkTopGap === 'string' ? input.linkTopGap.trim() : ''

  return {
    labelGap: labelGap || DEFAULT_QUICK_START_RHYTHM.labelGap,
    cardGap: cardGap || DEFAULT_QUICK_START_RHYTHM.cardGap,
    titleLineHeight: Number.isFinite(titleLineHeight)
      ? titleLineHeight
      : DEFAULT_QUICK_START_RHYTHM.titleLineHeight,
    summaryLineHeight: Number.isFinite(summaryLineHeight)
      ? summaryLineHeight
      : DEFAULT_QUICK_START_RHYTHM.summaryLineHeight,
    summaryMaxWidth: summaryMaxWidth || DEFAULT_QUICK_START_RHYTHM.summaryMaxWidth,
    linkTopGap: linkTopGap || DEFAULT_QUICK_START_RHYTHM.linkTopGap,
  }
}
