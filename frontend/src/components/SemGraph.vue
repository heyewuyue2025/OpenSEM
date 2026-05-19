<template>
  <div class="sem-graph">
    <div v-if="!ready" class="placeholder">
      <p>图渲染依赖尚未加载或缺少模型语法。</p>
    </div>
    <div ref="el" class="cy"></div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  lavaanSyntax: { type: String, default: '' },
  estimates: { type: Array, default: () => [] }, // [{lval,op,rval,est_std,p_value,...}]
})

const el = ref(null)
const cyInstance = ref(null)
const ready = ref(false)

function toNum(v) {
  if (v === null || v === undefined) return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

function starForP(p) {
  const pv = toNum(p)
  if (pv === null) return ''
  if (pv < 0.001) return '***'
  if (pv < 0.01) return '**'
  if (pv < 0.05) return '*'
  return ''
}

function indexEstimates(list) {
  const m = new Map()
  for (const r of Array.isArray(list) ? list : []) {
    const lval = String(r?.lval ?? '').trim()
    const op = String(r?.op ?? '').trim()
    const rval = String(r?.rval ?? '').trim()
    if (!lval || !op || !rval) continue
    m.set(`${lval}|${op}|${rval}`, r)
  }
  return m
}

function parseLavaan(s, estMap) {
  const lines = String(s || '')
    .split('\n')
    .map((x) => x.trim())
    .filter(Boolean)

  const latent = new Set()
  const nodes = new Set()
  const edges = []

  for (const line of lines) {
    if (line.includes('=~')) {
      const [lhsRaw, rhsRaw] = line.split('=~')
      const lhs = lhsRaw.trim()
      latent.add(lhs)
      nodes.add(lhs)
      const rhs = rhsRaw
        .split('+')
        .map((x) => x.trim())
        .filter(Boolean)
        .map((x) => x.replace(/^1\*/g, '').trim())
      for (const ind of rhs) {
        nodes.add(ind)
        const r = estMap.get(`${lhs}|=~|${ind}`)
        const beta = r?.est_std ?? null
        const p = r?.p_value ?? null
        const label = beta === null || beta === undefined ? '' : `β=${Number(beta).toFixed(3)}${starForP(p)}`
        edges.push({
          source: lhs,
          target: ind,
          kind: 'loading',
          label,
          p,
        })
      }
      continue
    }
    if (line.includes('~')) {
      const [lhsRaw, rhsRaw] = line.split('~')
      const toVar = lhsRaw.trim()
      nodes.add(toVar)
      const fromVars = rhsRaw
        .split('+')
        .map((x) => x.trim())
        .filter(Boolean)
      for (const fromVar of fromVars) {
        nodes.add(fromVar)
        const r = estMap.get(`${toVar}|~|${fromVar}`)
        const beta = r?.est_std ?? null
        const p = r?.p_value ?? null
        const label = beta === null || beta === undefined ? '' : `β=${Number(beta).toFixed(3)}${starForP(p)}`
        edges.push({
          source: fromVar,
          target: toVar,
          kind: 'path',
          label,
          p,
        })
      }
      continue
    }
    if (line.includes('~~')) {
      const [aRaw, bRaw] = line.split('~~')
      const a = aRaw.trim()
      const b = bRaw.trim()
      nodes.add(a)
      nodes.add(b)
      const r = estMap.get(`${a}|~~|${b}`) || estMap.get(`${b}|~~|${a}`)
      const p = r?.p_value ?? null
      edges.push({ source: a, target: b, kind: 'cov', label: '', p })
    }
  }

  return {
    nodes: [...nodes].map((id) => ({ id, isLatent: latent.has(id) })),
    edges,
  }
}

const graph = computed(() => {
  const estMap = indexEstimates(props.estimates)
  return parseLavaan(props.lavaanSyntax, estMap)
})

async function ensureCytoscape() {
  const mod = await import('cytoscape')
  return mod.default || mod
}

async function render() {
  const Cytoscape = await ensureCytoscape()
  if (!el.value) return

  const { nodes, edges } = graph.value
  if (!nodes.length) {
    ready.value = false
    if (cyInstance.value) {
      cyInstance.value.destroy()
      cyInstance.value = null
    }
    return
  }

  ready.value = true

  const elements = [
    ...nodes.map((n) => ({
      data: { id: n.id, label: n.id, isLatent: n.isLatent },
      classes: n.isLatent ? 'latent' : 'observed',
    })),
    ...edges.map((e, i) => {
      const pv = toNum(e.p)
      const sig = pv !== null && pv < 0.05
      return {
        data: { id: `e-${i}`, source: e.source, target: e.target, kind: e.kind, label: e.label || '', p: pv },
        classes: `${e.kind}${sig ? ' sig' : ''}`,
      }
    }),
  ]

  if (cyInstance.value) {
    cyInstance.value.json({ elements })
    cyInstance.value.layout({ name: 'breadthfirst', directed: true, padding: 24, spacingFactor: 1.25 }).run()
    return
  }

  cyInstance.value = Cytoscape({
    container: el.value,
    elements,
    style: [
      {
        selector: 'node',
        style: {
          label: 'data(label)',
          'text-valign': 'center',
          'text-halign': 'center',
          'font-size': 12,
          'font-family': 'ui-sans-serif, system-ui',
          color: '#1a1a1a',
          'background-color': '#fff',
          'border-width': 1,
          'border-color': '#d8d4cd',
          'padding': '6px',
        },
      },
      {
        selector: 'node.latent',
        style: {
          shape: 'ellipse',
          'border-color': '#c41e3a',
          'border-width': 2,
        },
      },
      {
        selector: 'node.observed',
        style: {
          shape: 'round-rectangle',
        },
      },
      {
        selector: 'edge',
        style: {
          width: 1.5,
          'line-color': '#8f8a80',
          'target-arrow-shape': 'triangle',
          'target-arrow-color': '#8f8a80',
          'curve-style': 'bezier',
          label: 'data(label)',
          'font-size': 10,
          'text-background-opacity': 1,
          'text-background-color': '#fff',
          'text-background-padding': '2px',
          'text-rotation': 'autorotate',
          color: '#1a1a1a',
        },
      },
      {
        selector: 'edge.sig',
        style: {
          width: 3,
          'line-color': '#c41e3a',
          'target-arrow-color': '#c41e3a',
        },
      },
      {
        selector: 'edge.cov',
        style: {
          'target-arrow-shape': 'none',
          'line-style': 'dashed',
          'line-color': '#8f8a80',
        },
      },
    ],
    layout: { name: 'breadthfirst', directed: true, padding: 24, spacingFactor: 1.25 },
  })
}

onMounted(() => {
  render()
})

watch(
  () => [props.lavaanSyntax, props.estimates],
  () => render()
)

onBeforeUnmount(() => {
  if (cyInstance.value) {
    cyInstance.value.destroy()
    cyInstance.value = null
  }
})
</script>

<style scoped>
.sem-graph {
  width: 100%;
}

.cy {
  height: 360px;
  width: 100%;
  background: var(--bg-paper);
  border: 1px solid var(--border-light);
}

.placeholder {
  padding: 0.75rem 0.9rem;
  color: var(--text-muted);
  background: var(--bg-paper);
  border: 1px solid var(--border-light);
  margin-bottom: 0.6rem;
  font-size: 0.9rem;
}
</style>

