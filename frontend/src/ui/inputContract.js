/**
 * 核心页 input / select / textarea 的 class 契约（单一来源，便于回归与命名一致）
 */

export const INP = Object.freeze({
  input: 'osem-input',
  select: 'osem-select',
  textarea: 'osem-textarea',
  fieldLabel: 'osem-field-label',
  /** 行内紧凑 select（变量类型、MI 风险筛选等） */
  selectCompact: 'osem-select osem-select--compact',
  /** 等宽多行（lavaan 语法预览等） */
  textareaMono: 'osem-textarea osem-textarea--mono',
  invalidInput: 'osem-input osem-input--invalid',
  invalidSelect: 'osem-select osem-select--invalid',
  invalidTextarea: 'osem-textarea osem-textarea--invalid',
})

/**
 * @param {string} [key]
 * @returns {string}
 */
export function pickInputVariant(key) {
  if (typeof key === 'string' && Object.prototype.hasOwnProperty.call(INP, key)) {
    return INP[key]
  }
  return INP.input
}
