<template>
  <div class="home-knowledge osem-core-page">
    <div class="doc-shell">
      <header class="doc-header">
        <p class="doc-eyebrow">{{ doc.eyebrow }}</p>
        <h1 class="doc-title">{{ doc.title }}</h1>
        <p class="doc-summary">{{ doc.summary }}</p>
        <div class="doc-actions">
          <router-link class="osem-btn osem-btn--secondary" to="/">返回首页</router-link>
          <router-link class="osem-btn osem-btn--primary" to="/data">进入数据导入</router-link>
        </div>
      </header>

      <main class="doc-main">
        <section v-for="section in doc.sections" :key="section.heading" class="doc-card osem-surface">
          <h2 class="doc-card-title">{{ section.heading }}</h2>
          <p class="doc-card-intro">{{ section.intro }}</p>
          <ul class="doc-list">
            <li v-for="item in section.bullets" :key="item">{{ item }}</li>
          </ul>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const DOCS = Object.freeze({
  'product-position': {
    eyebrow: 'PRODUCT POSITIONING',
    title: '产品定位',
    summary:
      'OpenSEM 面向高校科研、应用统计与业务研究团队，提供从数据导入到模型解释的结构方程分析闭环。它不是统计黑盒，而是强调可解释、可复核、可复用的研究型工作台。',
    sections: [
      {
        heading: '目标用户',
        intro: '平台设计默认服务以下高频场景：',
        bullets: [
          '社会科学与教育研究：问卷量表验证、潜变量关系检验',
          '医学与公共卫生：路径机制解释、群组差异比较',
          '企业研究与咨询：满意度驱动、机制路径与汇报输出',
          '教学与训练：用于结构方程课程演示与方法训练',
        ],
      },
      {
        heading: '核心价值边界',
        intro: 'OpenSEM 重点解决“流程复杂、解释困难、复现成本高”的问题。',
        bullets: [
          '聚焦 SEM 主流程，不扩张到无关的广义 BI 能力',
          '支持从“可运行”到“可解释”的结果过渡，而非只给参数表',
          '结果导出强调学术写作可用性，减少人工二次整理',
          '保留手动校验空间，避免过度自动化带来的误判',
        ],
      },
    ],
  },
  'core-value': {
    eyebrow: 'CORE VALUE',
    title: '核心价值',
    summary:
      '核心价值不是“更炫”，而是“更可信”。OpenSEM 以过程透明和结果可解释为主线，让模型结果能被团队共同审阅与复核。',
    sections: [
      {
        heading: '可解释',
        intro: '每一个关键指标都应可被说明，而不是孤立数字。',
        bullets: [
          '拟合指标提供上下文解释与判断提示',
          '路径显著性自动汇总为结构化结论，降低阅读门槛',
          '中介/调节结果保留统计意义与业务意义的双重表达',
          '术语提示用于团队沟通时统一统计语言',
        ],
      },
      {
        heading: '可追溯',
        intro: '分析链路可回看，便于版本对齐和复盘。',
        bullets: [
          '数据会话、模型语法、估算结果保持对应关系',
          '关键操作前后状态可被观察，减少“黑盒跳步”',
          '模型修改可快速回到建模页继续修正',
          '导出内容带有分析上下文，便于协作审阅',
        ],
      },
      {
        heading: '可复用',
        intro: '减少重复劳动，把精力留给研究判断本身。',
        bullets: [
          '同一数据会话可复用到建模与结果页',
          '常用分析流程可在团队内快速复现',
          '输出格式适配论文和汇报，缩短交付链路',
          '页面结构稳定，降低学习与交接成本',
        ],
      },
    ],
  },
  'analysis-flow': {
    eyebrow: 'ANALYSIS FLOW',
    title: '分析流程',
    summary:
      '建议流程遵循“数据质量 → 模型结构 → 拟合诊断 → 结果解释 → 导出汇报”。先保证输入质量，再追求模型复杂度，能显著降低返工率。',
    sections: [
      {
        heading: '步骤一：数据导入与检查',
        intro: '先确认变量与缺失处理策略，再进入建模。',
        bullets: [
          '完成文件导入后，检查变量类型与缺失率',
          '对高缺失变量提前确定 listwise / FIML / 插补策略',
          '明确样本规模、变量命名与量表结构',
          '确保数据会话有效，再进入模型搭建',
        ],
      },
      {
        heading: '步骤二：模型搭建与语法生成',
        intro: '由理论先行，工具补全。',
        bullets: [
          '先定义潜变量及其测量指标，再设置结构路径',
          '误差协变应有理论依据，避免经验性堆叠',
          '生成 lavaan 语法后先做一次校验',
          '必要时做最小修改并保留每次修改理由',
        ],
      },
      {
        heading: '步骤三：估算、诊断与解释',
        intro: '拟合指标和路径结果要联合判断。',
        bullets: [
          '先看整体拟合，再看关键路径显著性与方向',
          '对于复杂关系可补充 Bootstrap、中介与调节分析',
          '谨慎使用 MI 建议，优先考虑理论可解释性',
          '形成“结果段落 + 证据表格”的双轨输出',
        ],
      },
    ],
  },
  'trust-export': {
    eyebrow: 'TRUST & EXPORT',
    title: '可信与导出',
    summary:
      '可信来自可验证，导出来自可交付。OpenSEM 的输出目标不是“只导文件”，而是支持研究复核、团队协作和对外汇报。',
    sections: [
      {
        heading: '可信原则',
        intro: '输出前建议做一次最小可信检查清单。',
        bullets: [
          '确认语法版本与当前估算结果一致',
          '确认缺失处理策略与报告描述一致',
          '确认关键路径方向、显著性与理论预期一致',
          '确认是否存在过度依赖 MI 的修改风险',
        ],
      },
      {
        heading: '导出策略',
        intro: '不同场景使用不同导出组合。',
        bullets: [
          '论文写作：优先使用结构化指标表 + 结果段落',
          '组会汇报：保留路径摘要与关键解释提示',
          '跨团队协作：附带语法与关键参数版本信息',
          '对外交付：避免只给数值，补充方法说明与边界说明',
        ],
      },
      {
        heading: '风险提示',
        intro: '导出不是终点，解释质量决定结论质量。',
        bullets: [
          '单一指标良好不代表模型整体可靠',
          '显著性不等于实质性影响，需结合效应大小',
          '复杂模型需关注样本规模与估计稳定性',
          '最终稿件应由研究者完成人工复核与语义润色',
        ],
      },
    ],
  },
})

const FALLBACK_DOC = DOCS['product-position']

const doc = computed(() => {
  const key = String(route.params.topic || '').trim()
  return DOCS[key] || FALLBACK_DOC
})
</script>

<style scoped>
.home-knowledge {
  min-height: 100%;
  --osem-core-bg-nebula-a: rgba(111, 172, 252, 0.2);
  --osem-core-bg-nebula-b: rgba(242, 168, 112, 0.14);
  --osem-core-bg-nebula-c: rgba(126, 153, 238, 0.14);
}

.doc-shell {
  max-width: 1080px;
  margin: 0 auto;
  padding: clamp(1rem, 3.2vw, 2.2rem);
}

.doc-header {
  padding: 1rem 1.1rem 1.1rem;
  border: 1px solid var(--line-strong);
  border-radius: 14px;
  background: linear-gradient(145deg, rgba(10, 19, 35, 0.92), rgba(7, 14, 26, 0.94));
  box-shadow: var(--shadow-glow);
}

.doc-eyebrow {
  margin: 0;
  font-size: 0.74rem;
  letter-spacing: 0.12em;
  color: var(--panel-subtitle);
}

.doc-title {
  margin: 0.35rem 0 0;
  font-size: clamp(1.5rem, 2.3vw, 2.2rem);
  line-height: 1.2;
  color: var(--panel-title);
}

.doc-summary {
  margin: 0.65rem 0 0;
  max-width: 72ch;
  font-size: 0.95rem;
  line-height: 1.75;
  color: var(--text-secondary);
}

.doc-actions {
  margin-top: 0.85rem;
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.doc-main {
  margin-top: 0.9rem;
  display: grid;
  gap: 0.8rem;
}

.doc-card {
  padding: 0.95rem 1rem;
}

.doc-card-title {
  margin: 0;
  font-size: 1.05rem;
  color: var(--panel-title);
}

.doc-card-intro {
  margin: 0.4rem 0 0;
  color: var(--text-secondary);
  line-height: 1.65;
}

.doc-list {
  margin: 0.5rem 0 0;
  padding-left: 1.05rem;
  color: var(--text-secondary);
  line-height: 1.6;
}

.doc-list li {
  margin: 0.28rem 0;
}
</style>
