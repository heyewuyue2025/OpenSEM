<template>
  <span class="term-tip">
    <button
      ref="btnEl"
      type="button"
      class="term-tip-btn"
      :aria-label="`术语解释：${entry?.title || entry?.label || term}`"
      @mouseenter="handleTriggerEnter"
      @mouseleave="handleTriggerLeave"
      @focus="handleTriggerEnter"
      @blur="handleTriggerLeave"
      @click="toggleOpen"
    >
      ?
    </button>
    <Teleport to="body">
      <div
        v-if="open && entry"
        ref="popEl"
        class="term-tip-pop"
        :style="popStyle"
        role="tooltip"
        @mouseenter="handlePopEnter"
        @mouseleave="handlePopLeave"
      >
        <div class="term-tip-title">{{ entry.title || entry.label }}</div>
        <ul v-if="Array.isArray(entry.lines) && entry.lines.length" class="term-tip-lines">
          <li v-for="(line, idx) in entry.lines" :key="`${ns}-${term}-${idx}`">{{ line }}</li>
        </ul>
      </div>
    </Teleport>
  </span>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import { getGlossaryEntry } from '../content/glossary'

const props = defineProps({
  ns: { type: String, default: 'fit' },
  term: { type: String, required: true },
})

const open = ref(false)
const btnEl = ref(null)
const popEl = ref(null)
const popStyle = ref({})
const entry = computed(() => getGlossaryEntry(props.ns, props.term))
let closeTimer = null

function clearCloseTimer() {
  if (!closeTimer) return
  clearTimeout(closeTimer)
  closeTimer = null
}

function scheduleClose() {
  clearCloseTimer()
  closeTimer = setTimeout(() => {
    open.value = false
    closeTimer = null
  }, 120)
}

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v))
}

function updatePopoverPosition() {
  const btn = btnEl.value
  const pop = popEl.value
  if (!btn || !pop) return
  const btnRect = btn.getBoundingClientRect()
  const popRect = pop.getBoundingClientRect()
  const pad = 10
  const gap = 8
  const viewportW = window.innerWidth
  const viewportH = window.innerHeight

  const left = clamp(btnRect.left + btnRect.width / 2 - popRect.width / 2, pad, viewportW - popRect.width - pad)
  let top = btnRect.bottom + gap
  if (top + popRect.height > viewportH - pad) {
    top = Math.max(pad, btnRect.top - popRect.height - gap)
  }
  popStyle.value = {
    left: `${Math.round(left)}px`,
    top: `${Math.round(top)}px`,
  }
}

function openPopover() {
  clearCloseTimer()
  open.value = true
  nextTick(() => {
    updatePopoverPosition()
  })
}

function handleTriggerEnter() {
  openPopover()
}

function handleTriggerLeave() {
  scheduleClose()
}

function handlePopEnter() {
  clearCloseTimer()
}

function handlePopLeave() {
  scheduleClose()
}

function toggleOpen() {
  if (open.value) {
    open.value = false
    clearCloseTimer()
    return
  }
  openPopover()
}

function handleViewportChange() {
  if (!open.value) return
  updatePopoverPosition()
}

window.addEventListener('scroll', handleViewportChange, true)
window.addEventListener('resize', handleViewportChange)

onBeforeUnmount(() => {
  clearCloseTimer()
  window.removeEventListener('scroll', handleViewportChange, true)
  window.removeEventListener('resize', handleViewportChange)
})
</script>

<style scoped>
.term-tip {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.term-tip-btn {
  width: 16px;
  height: 16px;
  padding: 0;
  border-radius: 999px;
  border: 1px solid var(--border-light);
  background: #fff;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 14px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: border-color var(--transition-fast), color var(--transition-fast), background var(--transition-fast);
}

.term-tip-btn:hover {
  border-color: var(--accent-cta);
  color: var(--accent-cta);
  background: var(--accent-cta-subtle);
}

.term-tip-pop {
  position: fixed;
  z-index: 5000;
  width: min(320px, 70vw);
  padding: 0.6rem 0.65rem;
  border: 1px solid var(--line-strong, var(--border));
  background: var(--surface-elevated, var(--panel));
  border-radius: 12px;
  box-shadow: var(--shadow-glow, 0 14px 30px rgba(0, 0, 0, 0.24));
  backdrop-filter: blur(8px);
}

.term-tip-title {
  font-weight: 700;
  color: var(--text-primary);
  font-size: 0.86rem;
  margin-bottom: 0.35rem;
}

.term-tip-lines {
  margin: 0;
  padding-left: 1.05rem;
  color: var(--text-secondary);
  font-size: 0.8rem;
  line-height: 1.35;
}

.term-tip-lines li {
  margin: 0.2rem 0;
}
</style>

