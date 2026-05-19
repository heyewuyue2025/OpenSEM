const DEFAULT_WORKFLOW_COPY = Object.freeze({
  sectionLabel: 'WORKFLOW / 分析流程',
  steps: Object.freeze([
    Object.freeze({ path: '/data', title: '数据管理', desc: '数据导入 · 变量预览' }),
    Object.freeze({ path: '/model', title: '表单建模', desc: 'CFA 建模 · 路径设定 · 误差协变' }),
    Object.freeze({ path: '/results', title: '结果与导出', desc: '拟合度解读 · APA 表格导出' }),
  ]),
})

const WORKFLOW_DESC_SYNONYMS = new Map([
  ['导入 · 变量预览', '数据导入 · 变量预览'],
  ['CFA · 路径 · 误差协变', 'CFA 建模 · 路径设定 · 误差协变'],
  ['拟合度 · APA 表格', '拟合度解读 · APA 表格导出'],
])

function normalizeText(value, fallback) {
  if (typeof value !== 'string') return fallback
  const trimmed = value.trim()
  return trimmed || fallback
}

function normalizeStep(step, fallback) {
  if (!step || typeof step !== 'object') {
    return { ...fallback }
  }
  const descCandidate = normalizeText(step.desc, fallback.desc)
  return {
    path: fallback.path,
    title: normalizeText(step.title, fallback.title),
    desc: WORKFLOW_DESC_SYNONYMS.get(descCandidate) || descCandidate,
  }
}

export function resolveWorkflowCopy(input) {
  if (!input || typeof input !== 'object') {
    return {
      sectionLabel: DEFAULT_WORKFLOW_COPY.sectionLabel,
      steps: DEFAULT_WORKFLOW_COPY.steps.map((step) => ({ ...step })),
    }
  }

  const incomingSteps = Array.isArray(input.steps) ? input.steps : []
  return {
    sectionLabel: normalizeText(input.sectionLabel, DEFAULT_WORKFLOW_COPY.sectionLabel),
    steps: DEFAULT_WORKFLOW_COPY.steps.map((fallbackStep, idx) =>
      normalizeStep(incomingSteps[idx], fallbackStep),
    ),
  }
}
