import { BTN, pickButtonVariant } from '../../ui/buttonContract'

const DEFAULT_CTAS = Object.freeze([
  {
    id: 'primary',
    label: '立即开始',
    to: '/data',
    variant: BTN.primary,
  },
  {
    id: 'secondary',
    label: '查看演示',
    to: '/results',
    variant: BTN.secondaryMuted,
  },
])

export function resolveHeroCtas(input) {
  if (!Array.isArray(input) || input.length === 0) {
    return [...DEFAULT_CTAS]
  }
  return input
    .filter((item) => item && typeof item.label === 'string' && typeof item.to === 'string')
    .map((item, index) => ({
      id: item.id || `cta-${index}`,
      label: item.label.trim() || `CTA-${index + 1}`,
      to: item.to.trim() || '/data',
      variant: pickButtonVariant(item.variantKey),
    }))
}
