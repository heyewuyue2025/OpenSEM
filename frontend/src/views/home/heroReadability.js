const DEFAULT_HERO_READABILITY = Object.freeze({
  quoteWeight: 720,
  quoteLineHeight: 1.22,
  subtitleLineHeight: 1.8,
  subtitleMaxWidth: '700px',
  assistiveLineHeight: 1.68,
  blockGap: '0.9rem',
})

export function resolveHeroReadability(input) {
  if (!input || typeof input !== 'object') {
    return { ...DEFAULT_HERO_READABILITY }
  }

  const quoteWeight = Number(input.quoteWeight)
  const quoteLineHeight = Number(input.quoteLineHeight)
  const subtitleLineHeight = Number(input.subtitleLineHeight)
  const assistiveLineHeight = Number(input.assistiveLineHeight)
  const subtitleMaxWidth =
    typeof input.subtitleMaxWidth === 'string' ? input.subtitleMaxWidth.trim() : ''
  const blockGap = typeof input.blockGap === 'string' ? input.blockGap.trim() : ''

  return {
    quoteWeight: Number.isFinite(quoteWeight) ? quoteWeight : DEFAULT_HERO_READABILITY.quoteWeight,
    quoteLineHeight: Number.isFinite(quoteLineHeight)
      ? quoteLineHeight
      : DEFAULT_HERO_READABILITY.quoteLineHeight,
    subtitleLineHeight: Number.isFinite(subtitleLineHeight)
      ? subtitleLineHeight
      : DEFAULT_HERO_READABILITY.subtitleLineHeight,
    subtitleMaxWidth: subtitleMaxWidth || DEFAULT_HERO_READABILITY.subtitleMaxWidth,
    assistiveLineHeight: Number.isFinite(assistiveLineHeight)
      ? assistiveLineHeight
      : DEFAULT_HERO_READABILITY.assistiveLineHeight,
    blockGap: blockGap || DEFAULT_HERO_READABILITY.blockGap,
  }
}
