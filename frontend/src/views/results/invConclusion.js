export function buildInvOneLineConclusion({ conclusion, lite = false } = {}) {
  const c = conclusion && typeof conclusion === 'object' ? conclusion : {}
  const level = String(c.level || 'NA')
  if (level === 'NA') return '一句话结论：本研究的测量不变性序列结果不足，暂无法给出可用于论文的等值结论。'
  if (lite) {
    if (c.ok === true) {
      return `一句话结论（lite）：在常用经验阈值下，本研究在多群组间的测量模型至少达到 ${level} 不变性（建议仍结合理论合理性）。`
    }
    return `一句话结论（lite）：在常用经验阈值下，本研究未能支持到 scalar/strict 的等值结论（当前最高可接受层级：${level}）。`
  }
  if (c.ok === true) {
    return '一句话结论（strict）：在常用经验阈值下，本研究在多群组间的测量模型达到 strict 不变性（建议仍结合理论合理性）。'
  }
  return `一句话结论（strict）：在常用经验阈值下，本研究未能支持到 strict 不变性（当前最高可接受层级：${level}）。`
}
