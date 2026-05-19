const DEFAULT_QUICK_ACTIONS_COPY = Object.freeze({
  sectionLabel: 'QUICK ACTIONS / 快捷入口',
  actions: Object.freeze([
    Object.freeze({ to: '/data', label: '数据导入' }),
    Object.freeze({ to: '/model', label: '表单建模' }),
    Object.freeze({ to: '/results', label: '结果导出' }),
  ]),
})

const QUICK_ACTION_LABEL_SYNONYMS = new Map([
  ['上传数据', '数据导入'],
  ['新建模型', '表单建模'],
  ['导出结果', '结果导出'],
])

function normalizeText(value, fallback) {
  if (typeof value !== 'string') return fallback
  const trimmed = value.trim()
  return trimmed || fallback
}

function normalizeAction(action, fallback) {
  if (!action || typeof action !== 'object') {
    return { ...fallback }
  }
  const label = normalizeText(action.label, fallback.label)
  return {
    to: fallback.to,
    label: QUICK_ACTION_LABEL_SYNONYMS.get(label) || label,
  }
}

export function resolveQuickActionsCopy(input) {
  if (!input || typeof input !== 'object') {
    return {
      sectionLabel: DEFAULT_QUICK_ACTIONS_COPY.sectionLabel,
      actions: DEFAULT_QUICK_ACTIONS_COPY.actions.map((action) => ({ ...action })),
    }
  }

  const incomingActions = Array.isArray(input.actions) ? input.actions : []
  return {
    sectionLabel: normalizeText(input.sectionLabel, DEFAULT_QUICK_ACTIONS_COPY.sectionLabel),
    actions: DEFAULT_QUICK_ACTIONS_COPY.actions.map((fallbackAction, idx) =>
      normalizeAction(incomingActions[idx], fallbackAction),
    ),
  }
}
