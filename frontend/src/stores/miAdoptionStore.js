import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const STORAGE_PREFIX = 'OpenSEM:mi:adoptions:v1:'

function safeJsonParse(raw) {
  try {
    return JSON.parse(raw)
  } catch (_) {
    return null
  }
}

function nowIso() {
  return new Date().toISOString()
}

function newUuid() {
  try {
    if (globalThis?.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  } catch (_) {
    // ignore
  }
  // fallback: not cryptographically strong, but sufficient for local adoption tracking
  return `mi_${Date.now()}_${Math.random().toString(16).slice(2)}`
}

function normalizeMiItem(raw) {
  const lhs = String(raw?.lhs ?? '').trim()
  const op = String(raw?.op ?? '').trim()
  const rhs = String(raw?.rhs ?? '').trim()
  const mi = raw?.mi ?? null
  const epc = raw?.epc ?? null
  const source = String(raw?.source ?? '').trim() || 'lavaan::modindices'
  return {
    lhs,
    op,
    rhs,
    mi,
    epc,
    source,
    raw: raw && typeof raw === 'object' ? raw : {},
  }
}

export const useMiAdoptionStore = defineStore('miAdoptions', () => {
  const byTag = ref({})

  function _key(tag) {
    const t = String(tag || '').trim()
    return STORAGE_PREFIX + (t || '—')
  }

  function loadTag(tag) {
    const k = _key(tag)
    try {
      const raw = localStorage.getItem(k)
      if (!raw) {
        byTag.value = { ...byTag.value, [k]: [] }
        return []
      }
      const d = safeJsonParse(raw)
      const arr = Array.isArray(d) ? d : []
      byTag.value = { ...byTag.value, [k]: arr }
      return arr
    } catch (_) {
      byTag.value = { ...byTag.value, [k]: [] }
      return []
    }
  }

  function getForTag(tag) {
    const k = _key(tag)
    if (!Object.prototype.hasOwnProperty.call(byTag.value, k)) {
      return loadTag(tag)
    }
    return byTag.value[k] || []
  }

  function addAdoption(record, { bucketTag } = {}) {
    const tag = String(bucketTag || record?.after_syntax_fingerprint || '').trim() || '—'
    const k = _key(tag)
    const existing = getForTag(tag)
    const next = [record, ...existing].slice(0, 1000)
    byTag.value = { ...byTag.value, [k]: next }
    try {
      localStorage.setItem(k, JSON.stringify(next))
    } catch (_) {
      // ignore
    }
    return record
  }

  function updateRecordInTag(tag, id, patch) {
    const t = String(tag || '').trim() || '—'
    const k = _key(t)
    const existing = getForTag(t)
    const next = existing.map((r) => {
      if (!r || String(r.id || '') !== String(id || '')) return r
      return { ...r, ...(patch && typeof patch === 'object' ? patch : {}) }
    })
    byTag.value = { ...byTag.value, [k]: next }
    try {
      localStorage.setItem(k, JSON.stringify(next))
    } catch (_) {
      // ignore
    }
    return next
  }

  function makeRecord({
    miItem,
    appliedTo = 'syntax',
    beforeSyntaxFingerprint,
    afterSyntaxFingerprint,
    beforeSyntaxText,
    afterSyntaxText,
    beforeModelForm,
    afterModelForm,
    notes,
  }) {
    return {
      id: newUuid(),
      mi_item_snapshot: normalizeMiItem(miItem),
      applied_to: appliedTo,
      applied_at: nowIso(),
      before_syntax_fingerprint: String(beforeSyntaxFingerprint || '').trim() || '—',
      after_syntax_fingerprint: String(afterSyntaxFingerprint || '').trim() || '—',
      before_syntax_text: String(beforeSyntaxText ?? ''),
      after_syntax_text: String(afterSyntaxText ?? ''),
      before_model_form: beforeModelForm && typeof beforeModelForm === 'object' ? beforeModelForm : null,
      after_model_form: afterModelForm && typeof afterModelForm === 'object' ? afterModelForm : null,
      undone_at: '',
      undone_reason: '',
      notes: notes ? String(notes) : '',
    }
  }

  const totalCachedBuckets = computed(() => Object.keys(byTag.value || {}).length)

  return {
    loadTag,
    getForTag,
    addAdoption,
    updateRecordInTag,
    makeRecord,
    totalCachedBuckets,
  }
})

