export const GLOSSARY = {
  fit: {
    chi2_df: {
      label: 'χ²/df',
      title: '卡方自由度比（χ²/df）',
      lines: [
        '衡量模型与数据偏离程度的一个粗略指标；越小通常表示拟合越好。',
        '经验阈值（仅供快速判断）：< 3 通常较好；3–5 临界；> 5 偏差较大。',
        '提示：χ² 对样本量敏感，建议与 CFI/TLI/RMSEA/SRMR 综合判断。',
      ],
    },
    rmsea: {
      label: 'RMSEA',
      title: '近似误差均方根（RMSEA）',
      lines: [
        '反映模型在总体层面的近似误差；越小越好。',
        '经验阈值：< 0.06 较好；0.06–0.10 可接受边界；> 0.10 偏高。',
        '提示：置信区间与模型复杂度也会影响解读，避免只看单一数值。',
      ],
    },
    cfi: {
      label: 'CFI',
      title: '比较拟合指数（CFI）',
      lines: [
        '将当前模型与“独立模型”（变量互不相关）对比得到的拟合提升；越接近 1 越好。',
        '经验阈值：≥ 0.95 通常很好；≥ 0.90 通常可接受；< 0.90 提示拟合偏弱。',
      ],
    },
    tli: {
      label: 'TLI',
      title: 'Tucker–Lewis 指数（TLI）',
      lines: [
        '与 CFI 类似的比较型拟合指数，并对模型复杂度有一定惩罚；越接近 1 越好。',
        '经验阈值：≥ 0.95 通常较好；≥ 0.90 可接受；< 0.90 偏弱。',
      ],
    },
    srmr: {
      label: 'SRMR',
      title: '标准化残差均方根（SRMR）',
      lines: [
        '基于相关/协方差残差的总体量化；越小表示残差越小、拟合越好。',
        '经验阈值：< 0.08 通常可接受；0.08–0.10 临界；> 0.10 偏高。',
      ],
    },
  },
  data: {
    data_key: {
      label: 'data_key',
      title: '数据会话键（data_key）',
      lines: [
        '后端解析上传数据后返回的临时标识，用于后续建模、估算与导出请求。',
        '若后端重启或缓存过期，该键会失效，需要重新上传数据。',
      ],
    },
    missing_strategy: {
      label: '缺失值处理',
      title: '缺失值处理策略（Missing Strategy）',
      lines: [
        '当变量缺失率较高时，需要先声明处理策略，避免估算结果含义不明确。',
        '常见策略有列表删除、FIML 与均值插补，建议结合研究设计解释其影响。',
      ],
    },
  },
  model: {
    latent_var: {
      label: '潜变量',
      title: '潜变量（Latent Variable）',
      lines: [
        '不可直接观测的抽象构念，通常由多个题项或观测指标共同测量。',
        '在 CFA/SEM 中，常通过载荷关系定义（例如 F =~ x1 + x2 + x3）。',
      ],
    },
    path: {
      label: '结构路径',
      title: '结构路径（Structural Path）',
      lines: [
        '表示变量之间的回归关系，常写作 Y ~ X，含义是 X 预测 Y。',
        '路径方向应基于理论假设，而非仅凭统计显著性决定。',
      ],
    },
    error_covariance: {
      label: '误差协变',
      title: '误差协变（Error Covariance）',
      lines: [
        '两个指标残差项之间允许相关，常用于处理共同方法偏差或题项措辞相近。',
        '应以理论依据或修正指数为前提，避免过度添加导致模型可解释性下降。',
      ],
    },
  },
}

export function getGlossaryEntry(namespace, key) {
  const ns = GLOSSARY?.[namespace]
  if (!ns) return null
  return ns?.[key] || null
}

