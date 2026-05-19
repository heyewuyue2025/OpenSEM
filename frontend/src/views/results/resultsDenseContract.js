/**
 * Results 高密区（MI / 不变性）布局 token 与 class 名契约。
 * 视觉实现以 `opensem-results-dense.css` 为准；本模块用于回归断言与单测兜底。
 */

export const DENSE = Object.freeze({
  rootModifier: 'osem-results-dense',
  zone: 'osem-dense-zone',
})

const DEFAULT = Object.freeze({
  tablet768: Object.freeze({
    miListGap: '0.55rem',
    miItemPadY: '0.5rem',
    miItemPadX: '0.55rem',
    invCardPad: '0.75rem',
    invCardRowGap: '0.45rem',
    invCardLabelCol: '88px',
    invReportPreLineHeight: 1.55,
  }),
  mobile375: Object.freeze({
    miListGap: '0.5rem',
    miItemPadY: '0.45rem',
    miItemPadX: '0.5rem',
    miTagFontRem: 0.65,
    invCardPad: '0.65rem',
    invCardLabelCol: 'minmax(0, 7.2rem)',
    invReportPreFontRem: 0.72,
    estTableMinWidth: 'max(100%, 520px)',
  }),
})

function numOr(v, d) {
  const n = Number(v)
  return Number.isFinite(n) ? n : d
}

function strOr(v, d) {
  if (typeof v !== 'string') return d
  const t = v.trim()
  return t || d
}

/**
 * @param {unknown} input
 * @returns {{ tablet768: Record<string, string|number>, mobile375: Record<string, string|number> }}
 */
export function resolveResultsDenseTokens(input) {
  if (!input || typeof input !== 'object') {
    return {
      tablet768: { ...DEFAULT.tablet768 },
      mobile375: { ...DEFAULT.mobile375 },
    }
  }

  const t768 = input.tablet768 && typeof input.tablet768 === 'object' ? input.tablet768 : {}
  const m375 = input.mobile375 && typeof input.mobile375 === 'object' ? input.mobile375 : {}

  return {
    tablet768: {
      miListGap: strOr(t768.miListGap, DEFAULT.tablet768.miListGap),
      miItemPadY: strOr(t768.miItemPadY, DEFAULT.tablet768.miItemPadY),
      miItemPadX: strOr(t768.miItemPadX, DEFAULT.tablet768.miItemPadX),
      invCardPad: strOr(t768.invCardPad, DEFAULT.tablet768.invCardPad),
      invCardRowGap: strOr(t768.invCardRowGap, DEFAULT.tablet768.invCardRowGap),
      invCardLabelCol: strOr(t768.invCardLabelCol, DEFAULT.tablet768.invCardLabelCol),
      invReportPreLineHeight: numOr(
        t768.invReportPreLineHeight,
        DEFAULT.tablet768.invReportPreLineHeight,
      ),
    },
    mobile375: {
      miListGap: strOr(m375.miListGap, DEFAULT.mobile375.miListGap),
      miItemPadY: strOr(m375.miItemPadY, DEFAULT.mobile375.miItemPadY),
      miItemPadX: strOr(m375.miItemPadX, DEFAULT.mobile375.miItemPadX),
      miTagFontRem: numOr(m375.miTagFontRem, DEFAULT.mobile375.miTagFontRem),
      invCardPad: strOr(m375.invCardPad, DEFAULT.mobile375.invCardPad),
      invCardLabelCol: strOr(m375.invCardLabelCol, DEFAULT.mobile375.invCardLabelCol),
      invReportPreFontRem: numOr(m375.invReportPreFontRem, DEFAULT.mobile375.invReportPreFontRem),
      estTableMinWidth: strOr(m375.estTableMinWidth, DEFAULT.mobile375.estTableMinWidth),
    },
  }
}

/**
 * 将 token 展平为可挂到 :root 或容器上的内联 style（CSS 变量名前缀 --osem-dense-）
 * @param {ReturnType<typeof resolveResultsDenseTokens>} tokens
 * @returns {Record<string, string|number>}
 */
export function toDenseInlineStyleVars(tokens) {
  const t = resolveResultsDenseTokens(tokens)
  return {
    '--osem-dense-mi-list-gap-768': t.tablet768.miListGap,
    '--osem-dense-mi-item-pad-y-768': t.tablet768.miItemPadY,
    '--osem-dense-mi-item-pad-x-768': t.tablet768.miItemPadX,
    '--osem-dense-inv-card-pad-768': t.tablet768.invCardPad,
    '--osem-dense-inv-row-gap-768': t.tablet768.invCardRowGap,
    '--osem-dense-inv-label-col-768': t.tablet768.invCardLabelCol,
    '--osem-dense-inv-pre-lh-768': t.tablet768.invReportPreLineHeight,
    '--osem-dense-mi-list-gap-375': t.mobile375.miListGap,
    '--osem-dense-mi-item-pad-y-375': t.mobile375.miItemPadY,
    '--osem-dense-mi-item-pad-x-375': t.mobile375.miItemPadX,
    '--osem-dense-mi-tag-rem-375': t.mobile375.miTagFontRem,
    '--osem-dense-inv-card-pad-375': t.mobile375.invCardPad,
    '--osem-dense-inv-label-col-375': t.mobile375.invCardLabelCol,
    '--osem-dense-inv-pre-rem-375': t.mobile375.invReportPreFontRem,
    '--osem-dense-est-minw-375': t.mobile375.estTableMinWidth,
  }
}
