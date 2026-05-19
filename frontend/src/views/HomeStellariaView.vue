<template>
  <div class="home" :style="parallaxStyle">
    <div class="nebula" aria-hidden="true"></div>
    <div class="pointer-glow" aria-hidden="true"></div>
    <div class="pointer-ripple" aria-hidden="true">
      <span :key="rippleId" class="pointer-ripple-dot ring-a" :style="{ left: `${rippleX}px`, top: `${rippleY}px` }"></span>
      <span :key="`${rippleId}-b`" class="pointer-ripple-dot ring-b" :style="{ left: `${rippleX}px`, top: `${rippleY}px` }"></span>
    </div>
    <div class="stars" aria-hidden="true"></div>
    <div class="spark-layer" aria-hidden="true">
      <span v-for="spark in sparkNodes" :key="spark.id" class="spark" :style="spark.style"></span>
    </div>

    <section
      ref="frameEl"
      class="frame"
      :class="{ loaded: hasLoaded }"
      @mousemove="handleMouseMove"
      @click="handlePointerClick"
      @mouseenter="setPointerActive(true)"
      @mouseleave="resetParallax"
    >
      <header class="scene-top">
        <div class="scene-brand reveal-item">
          <span class="dot"></span>
          <span class="brand-name">OpenSEM</span>
          <span class="brand-meta">Structural Equation Modeling Platform</span>
        </div>
        <nav class="scene-nav reveal-item">
          <router-link to="/home/product-position">产品定位</router-link>
          <router-link to="/home/core-value">核心价值</router-link>
          <router-link to="/home/analysis-flow">分析流程</router-link>
          <router-link to="/home/trust-export">可信与导出</router-link>
        </nav>
      </header>

      <div class="scene-body" id="intro">
        <div class="left-copy reveal-item">
          <p class="archive">RESEARCH-GRADE SEM WORKFLOW</p>
          <p class="season">面向高校科研与数据分析用户</p>
          <h1 class="title">
            <span class="title-en">OpenSEM</span>
            <span class="accent">结构方程</span>
            <span>建模平台</span>
          </h1>
          <p id="manifesto" class="manifesto">
            OpenSEM 将复杂统计分析收敛为可执行任务闭环：上传数据、表单建模、估算诊断、结果导出。
            在高复杂 SEM 场景下，提供低门槛、可解释、可追溯、可回归的完整分析体验。
          </p>
          <div id="guide" class="actions">
            <router-link
              to="/data"
              class="btn primary magnet-item"
              @mousemove="handleMagnetMove"
              @mouseleave="resetMagnet"
            >
              立即开始分析
            </router-link>
            <router-link
              to="/model"
              class="btn ghost magnet-item"
              @mousemove="handleMagnetMove"
              @mouseleave="resetMagnet"
            >
              查看建模流程
            </router-link>
          </div>
        </div>

        <aside class="planet-zone reveal-item">
          <div class="orbit-ring ring-1" aria-hidden="true"></div>
          <div class="orbit-ring ring-2" aria-hidden="true"></div>
          <div class="hero-image-shell">
            <img class="hero-image" :src="heroMainImageUrl" alt="OpenSEM 主视觉图" />
            <div class="hero-image-overlay" aria-hidden="true"></div>
          </div>
        </aside>
      </div>

      <footer id="about" class="scene-foot reveal-item">
        <span class="line"></span>
        <p class="foot-text">UPLOAD - MODEL - ESTIMATE - DIAGNOSE - EXPORT</p>
      </footer>
      <div class="scanline" aria-hidden="true"></div>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useDataStore } from '../stores/dataStore'
import { useModelStore } from '../stores/modelStore'
import { useStatsStore } from '../stores/statsStore'

const dataStore = useDataStore()
const modelStore = useModelStore()
const statsStore = useStatsStore()

const frameEl = ref(null)
const heroImageUrl = "url('/home-hero.png')"
const heroMainImageUrl = '/home-main-element.png'
const mouseX = ref(0)
const mouseY = ref(0)
const rippleId = ref(0)
const rippleX = ref(0)
const rippleY = ref(0)
const hasLoaded = ref(false)
const now = ref(Date.now())
let clockTimer = null

const sparkNodes = createSparkNodes(24)

const sampleN = computed(() => statsStore.nUsed || dataStore.nRows || '—')
const latentCount = computed(() => {
  const syntax = modelStore.lavaanSyntax || ''
  if (!syntax.trim()) return '—'
  return syntax
    .split('\n')
    .map((s) => s.trim())
    .filter((line) => line.includes('=~')).length
})
const cfiValue = computed(() => {
  const cfi = statsStore.fitIndices?.cfi
  if (cfi === null || cfi === undefined || cfi === '-') return '—'
  return String(cfi)
})
const timeNow = computed(() =>
  new Date(now.value).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
)

const parallaxStyle = computed(() => ({
  '--mx': mouseX.value.toFixed(4),
  '--my': mouseY.value.toFixed(4),
}))

function handleMouseMove(event) {
  if (!frameEl.value) return
  const rect = frameEl.value.getBoundingClientRect()
  if (!rect.width || !rect.height) return
  const normalizedX = (event.clientX - rect.left) / rect.width - 0.5
  const normalizedY = (event.clientY - rect.top) / rect.height - 0.5
  mouseX.value = Math.max(-0.5, Math.min(0.5, normalizedX))
  mouseY.value = Math.max(-0.5, Math.min(0.5, normalizedY))
  frameEl.value.style.setProperty('--pointer-x', `${event.clientX - rect.left}px`)
  frameEl.value.style.setProperty('--pointer-y', `${event.clientY - rect.top}px`)
}

function resetParallax() {
  mouseX.value = 0
  mouseY.value = 0
  if (frameEl.value) {
    frameEl.value.style.setProperty('--pointer-active', '0')
  }
}

function setPointerActive(active) {
  if (!frameEl.value) return
  frameEl.value.style.setProperty('--pointer-active', active ? '1' : '0')
}

function handlePointerClick(event) {
  if (!frameEl.value) return
  const rect = frameEl.value.getBoundingClientRect()
  rippleX.value = event.clientX - rect.left
  rippleY.value = event.clientY - rect.top
  rippleId.value += 1
}

function handleMagnetMove(event) {
  const target = event.currentTarget
  if (!target || !(target instanceof HTMLElement)) return
  const rect = target.getBoundingClientRect()
  const x = ((event.clientX - rect.left) / rect.width - 0.5) * 2
  const y = ((event.clientY - rect.top) / rect.height - 0.5) * 2
  target.style.setProperty('--magnet-x', `${Math.max(-1, Math.min(1, x))}`)
  target.style.setProperty('--magnet-y', `${Math.max(-1, Math.min(1, y))}`)
}

function resetMagnet(event) {
  const target = event.currentTarget
  if (!target || !(target instanceof HTMLElement)) return
  target.style.setProperty('--magnet-x', '0')
  target.style.setProperty('--magnet-y', '0')
}

function createSparkNodes(count) {
  return Array.from({ length: count }, (_, i) => {
    const left = ((i * 37 + 13) % 100) + '%'
    const top = ((i * 53 + 29) % 100) + '%'
    const delay = `${(i % 8) * 0.42}s`
    const duration = `${2.2 + (i % 5) * 0.58}s`
    const size = `${1.2 + (i % 4) * 0.8}px`
    return {
      id: `spark-${i}`,
      style: { left, top, animationDelay: delay, animationDuration: duration, width: size, height: size },
    }
  })
}

onMounted(() => {
  clockTimer = window.setInterval(() => {
    now.value = Date.now()
  }, 1000)
  requestAnimationFrame(() => {
    hasLoaded.value = true
  })
})

onBeforeUnmount(() => {
  if (clockTimer) {
    clearInterval(clockTimer)
    clockTimer = null
  }
})
</script>

<style scoped>
@font-face {
  font-family: 'DemoXieHei';
  src: url('/demo-xiehei.otf') format('opentype');
  font-display: swap;
}

.home {
  --mx: 0;
  --my: 0;
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  color: #f3f6ff;
  background: radial-gradient(circle at 70% 18%, #11386d 0%, rgba(17, 56, 109, 0) 36%), #04070f;
}

.nebula {
  position: absolute;
  inset: -8%;
  pointer-events: none;
  background:
    radial-gradient(circle at 20% 20%, rgba(120, 170, 255, 0.14), transparent 42%),
    radial-gradient(circle at 84% 30%, rgba(246, 161, 102, 0.13), transparent 44%),
    radial-gradient(circle at 65% 78%, rgba(82, 157, 255, 0.1), transparent 38%);
  filter: blur(8px);
  transform: translate(calc(var(--mx) * -28px), calc(var(--my) * -28px));
  transition: transform 220ms ease-out;
}

.stars {
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(circle at 12% 16%, rgba(255, 255, 255, 0.46) 0 1px, transparent 1.5px),
    radial-gradient(circle at 30% 70%, rgba(255, 255, 255, 0.34) 0 1px, transparent 1.5px),
    radial-gradient(circle at 70% 30%, rgba(255, 255, 255, 0.28) 0 1px, transparent 1.5px),
    radial-gradient(circle at 84% 60%, rgba(255, 255, 255, 0.22) 0 1px, transparent 1.5px),
    linear-gradient(180deg, rgba(3, 5, 12, 0.62), rgba(3, 6, 12, 0.92));
  background-size: 280px 280px, 340px 340px, 380px 380px, 420px 420px, 100% 100%;
  pointer-events: none;
  transform: translate(calc(var(--mx) * 20px), calc(var(--my) * 20px));
  transition: transform 180ms ease-out;
}

.spark-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.spark {
  position: absolute;
  border-radius: 999px;
  background: rgba(233, 244, 255, 0.9);
  box-shadow: 0 0 8px rgba(180, 219, 255, 0.7);
  opacity: 0.22;
  animation: spark-blink ease-in-out infinite;
}

.frame {
  --pointer-x: 50%;
  --pointer-y: 50%;
  --pointer-active: 0;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 1;
  min-height: 100vh;
  padding: clamp(1rem, 2vw, 1.5rem) clamp(1rem, 2.8vw, 2.3rem);
  border: 1px solid rgba(112, 136, 195, 0.3);
  margin: 0.6rem;
  background: linear-gradient(120deg, rgba(4, 8, 18, 0.92), rgba(5, 10, 22, 0.86));
  box-shadow: inset 0 0 0 1px rgba(125, 147, 200, 0.08);
  transform: perspective(1200px) rotateY(calc(var(--mx) * 4deg)) rotateX(calc(var(--my) * -4deg));
  transition: transform 180ms ease-out, box-shadow 260ms ease;
  transform-style: preserve-3d;
  isolation: isolate;
  overflow: hidden;
}

.frame > * {
  position: relative;
  z-index: 3;
}

.frame::before {
  content: '';
  position: absolute;
  inset: -6%;
  z-index: 0;
  background-image: v-bind(heroImageUrl);
  background-size: cover;
  background-position: center;
  filter: saturate(0.98) contrast(1.08) brightness(0.78);
  transform-origin: center;
  animation: kenburns 26s ease-in-out infinite alternate;
}

.frame::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 1;
  background:
    radial-gradient(circle at 76% 30%, rgba(255, 214, 154, 0.12), rgba(255, 214, 154, 0) 36%),
    radial-gradient(circle at 14% 70%, rgba(53, 117, 214, 0.18), rgba(53, 117, 214, 0) 42%),
    linear-gradient(140deg, rgba(2, 7, 16, 0.72), rgba(2, 7, 16, 0.82));
}

.frame.loaded {
  box-shadow:
    inset 0 0 0 1px rgba(125, 147, 200, 0.08),
    0 26px 60px rgba(0, 0, 0, 0.5),
    0 0 0 1px rgba(130, 169, 240, 0.06);
}

.pointer-glow {
  position: absolute;
  inset: 0;
  z-index: 8;
  pointer-events: none;
  opacity: calc(var(--pointer-active, 0) * 0.9);
  background: radial-gradient(180px circle at var(--pointer-x, 50%) var(--pointer-y, 50%), rgba(123, 196, 255, 0.24), rgba(123, 196, 255, 0) 70%);
  mix-blend-mode: screen;
  transition: opacity 180ms ease-out;
}

.pointer-ripple {
  position: absolute;
  inset: 0;
  z-index: 9;
  pointer-events: none;
}

.pointer-ripple-dot {
  position: absolute;
  width: 18px;
  height: 18px;
  border-radius: 999px;
  border: 1px solid rgba(164, 215, 255, 0.72);
  box-shadow: 0 0 0 1px rgba(98, 174, 255, 0.28) inset;
  transform: translate(-50%, -50%) scale(0.5);
  opacity: 0;
  animation: ripple-expand 560ms cubic-bezier(0.22, 1, 0.36, 1);
}

.pointer-ripple-dot.ring-b {
  border-color: rgba(255, 188, 130, 0.68);
  animation-duration: 720ms;
}

.scene-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.scene-brand {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.7rem;
  letter-spacing: 0.15em;
  color: #d3ddf7;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  border: 1px solid rgba(255, 165, 106, 0.8);
  box-shadow: 0 0 10px rgba(255, 165, 106, 0.55);
}

.brand-name { font-weight: 600; }
.brand-meta { opacity: 0.7; }

.scene-nav {
  display: inline-flex;
  gap: clamp(0.8rem, 2.4vw, 2rem);
  margin-left: auto;
}

.scene-nav a {
  color: #becbe8;
  text-decoration: none;
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  transition: transform 140ms ease, color 140ms ease, filter 140ms ease;
}

.scene-nav a:hover {
  color: #f4fbff;
  transform: translateY(-1px);
  filter: brightness(1.08);
}

.magnet-item {
  --magnet-x: 0;
  --magnet-y: 0;
}

.reserve-btn {
  justify-self: end;
  color: #e7eefc;
  text-decoration: none;
  font-size: 0.76rem;
  letter-spacing: 0.06em;
  border: 1px solid rgba(157, 178, 226, 0.4);
  padding: 0.52rem 0.88rem;
  border-radius: 999px;
  background: rgba(10, 19, 38, 0.8);
  transform: translate(calc(var(--magnet-x) * 4px), calc(var(--magnet-y) * 4px));
  transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
}

.reserve-btn:hover {
  border-color: rgba(182, 205, 255, 0.68);
  box-shadow: 0 10px 24px rgba(20, 40, 80, 0.45);
}

.scene-body {
  margin-top: clamp(1.2rem, 4vh, 2.3rem);
  display: grid;
  grid-template-columns: minmax(460px, 1fr) minmax(300px, 46%);
  align-items: center;
  gap: clamp(1.2rem, 3.4vw, 2.6rem);
}

.archive, .season {
  margin: 0;
  font-size: 0.72rem;
  letter-spacing: 0.2em;
  color: #9aacd4;
  text-transform: uppercase;
}

.season { margin-top: 0.36rem; }

.title {
  margin: clamp(0.9rem, 2.8vh, 2.1rem) 0 0;
  display: grid;
  font-family: "DemoXieHei", "Trebuchet MS", "Avenir Next", "Segoe UI", sans-serif;
  font-size: clamp(3rem, 8.8vw, 8.4rem);
  line-height: 0.88;
  letter-spacing: -0.03em;
  font-weight: 500;
}

.title .accent {
  color: #eca560;
  font-style: italic;
}

.title .title-en {
  letter-spacing: 0.015em;
  font-weight: 600;
}

.manifesto {
  margin: clamp(0.9rem, 2.2vh, 1.5rem) 0 0;
  max-width: 56ch;
  color: #c4d2ef;
  line-height: 1.85;
  font-size: 0.95rem;
  transform: translateY(56px);
}

.actions {
  margin-top: clamp(1rem, 2.6vh, 1.6rem);
  display: flex;
  gap: 0.8rem;
  transform: translateY(56px);
}

.btn {
  text-decoration: none;
  font-size: 0.82rem;
  letter-spacing: 0.08em;
  border-radius: 999px;
  padding: 0.62rem 1rem;
  border: 1px solid transparent;
  transform: translate(calc(var(--magnet-x) * 3px), calc(var(--magnet-y) * 3px));
  transition: transform 140ms ease, box-shadow 140ms ease, filter 140ms ease;
}

.btn.primary {
  color: #121f38;
  background: linear-gradient(140deg, #efc68f, #ef9e57);
}

.btn.ghost {
  color: #d6e1fa;
  border-color: rgba(167, 185, 229, 0.42);
  background: rgba(8, 16, 32, 0.7);
}

.btn:hover {
  filter: brightness(1.06);
  box-shadow: 0 8px 20px rgba(12, 25, 52, 0.5);
}

.planet-zone {
  position: relative;
  min-height: clamp(360px, 55vh, 620px);
}

.orbit-ring {
  position: absolute;
  left: 50%;
  top: 50%;
  border-radius: 999px;
  border: 1px solid rgba(129, 172, 241, 0.22);
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.orbit-ring.ring-1 {
  width: min(100%, 600px);
  aspect-ratio: 1 / 0.6;
  animation: orbit-drift 8s linear infinite;
}

.orbit-ring.ring-2 {
  width: min(78%, 470px);
  aspect-ratio: 1 / 0.56;
  opacity: 0.74;
  animation: orbit-drift 6.8s linear infinite reverse;
}

.planet {
  width: min(88%, 520px);
  aspect-ratio: 1 / 1;
  border-radius: 28px;
  margin: 0 auto;
  background: linear-gradient(160deg, rgba(163, 193, 245, 0.2), rgba(18, 37, 72, 0.36));
  box-shadow:
    inset 0 0 0 1px rgba(206, 214, 235, 0.15),
    0 0 0 1px rgba(153, 196, 255, 0.22),
    0 36px 60px rgba(0, 0, 0, 0.42);
  transform: translate(calc(var(--mx) * -16px), calc(var(--my) * -10px));
  transition: transform 180ms ease-out;
  animation: planet-float 7.5s ease-in-out infinite;
}

.hero-image-shell {
  position: relative;
  width: min(88%, 780px);
  aspect-ratio: 1 / 1;
  border-radius: 28px;
  overflow: hidden;
  margin: 0 auto;
  box-shadow:
    inset 0 0 0 1px rgba(206, 214, 235, 0.18),
    0 0 0 1px rgba(153, 196, 255, 0.24),
    0 36px 60px rgba(0, 0, 0, 0.45);
  transform: translate(calc(var(--mx) * -16px), calc(var(--my) * -10px + 10px));
  transition: transform 180ms ease-out;
  animation: planet-float 7.5s ease-in-out infinite;
}

.hero-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(1.04) contrast(1.06) brightness(0.9);
}

.hero-image-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 28% 20%, rgba(255, 214, 150, 0.2), rgba(255, 214, 150, 0) 36%),
    linear-gradient(180deg, rgba(6, 11, 22, 0.06), rgba(6, 11, 22, 0.28));
}

.telemetry {
  position: absolute;
  right: 0;
  top: 8%;
  width: min(220px, 45%);
  display: grid;
  gap: 0.45rem;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.telemetry div {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  color: #b5c6e8;
  border-bottom: 1px solid rgba(108, 128, 177, 0.3);
  padding-bottom: 0.28rem;
}

.telemetry strong {
  color: #e6f1ff;
  font-size: 0.76rem;
}

.scene-foot {
  margin-top: auto;
  padding-top: clamp(1rem, 2vh, 1.6rem);
  display: flex;
  align-items: center;
  gap: 0.7rem;
  transform: translateY(-12px);
}

.line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(149, 171, 216, 0.55), rgba(149, 171, 216, 0.06));
}

.foot-text {
  margin: 0;
  font-size: 0.7rem;
  letter-spacing: 0.2em;
  color: #8fa4d2;
  text-transform: uppercase;
}

.scanline {
  position: absolute;
  left: 0;
  right: 0;
  top: -28%;
  height: 28%;
  pointer-events: none;
  background: linear-gradient(180deg, rgba(130, 204, 255, 0.08), rgba(130, 204, 255, 0));
  animation: scan-pass 6s cubic-bezier(0.22, 1, 0.36, 1) infinite;
  mix-blend-mode: screen;
}

.reveal-item {
  opacity: 0;
  transform: translateY(16px);
  transition: opacity 600ms ease, transform 600ms ease;
}

.frame.loaded .reveal-item {
  opacity: 1;
  transform: translateY(0);
}

.frame.loaded .scene-nav { transition-delay: 80ms; }
.frame.loaded .reserve-btn { transition-delay: 120ms; }
.frame.loaded .left-copy { transition-delay: 160ms; }
.frame.loaded .planet-zone { transition-delay: 220ms; }
.frame.loaded .scene-foot { transition-delay: 260ms; }

@keyframes ripple-expand {
  0% { opacity: 0.85; transform: translate(-50%, -50%) scale(0.45); }
  75% { opacity: 0.24; }
  100% { opacity: 0; transform: translate(-50%, -50%) scale(5.2); }
}

@keyframes spark-blink {
  0%, 100% { opacity: 0.16; transform: scale(0.86); }
  50% { opacity: 0.92; transform: scale(1.2); }
}

@keyframes planet-float {
  0%, 100% { filter: brightness(1); }
  50% { filter: brightness(1.08); }
}

@keyframes orbit-drift {
  from { transform: translate(-50%, -50%) rotate(0deg); }
  to { transform: translate(-50%, -50%) rotate(360deg); }
}

@keyframes scan-pass {
  0% { transform: translateY(0); opacity: 0; }
  12% { opacity: 0.7; }
  45% { opacity: 0.18; }
  100% { transform: translateY(460%); opacity: 0; }
}

@keyframes kenburns {
  0% {
    transform: scale(1.02) translate3d(-1.2%, -0.6%, 0);
  }
  100% {
    transform: scale(1.11) translate3d(1.1%, 0.8%, 0);
  }
}

@media (max-width: 1024px) {
  .scene-body { grid-template-columns: 1fr; }
  .planet-zone { order: -1; min-height: auto; }
  .telemetry {
    position: static;
    margin: 1rem auto 0;
    width: min(420px, 100%);
  }
}

@media (max-width: 768px) {
  .scene-top {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.8rem;
  }
  .scene-nav {
    margin-left: 0;
    flex-wrap: wrap;
    gap: 0.6rem 1rem;
  }
  .reserve-btn { justify-self: start; }
  .title { font-size: clamp(2.45rem, 14vw, 4.5rem); }
  .actions { flex-wrap: wrap; }
  .scanline,
  .orbit-ring,
  .pointer-glow,
  .pointer-ripple { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  .nebula,
  .stars,
  .frame,
  .planet,
  .btn,
  .reserve-btn,
  .scene-nav a {
    transform: none !important;
    transition: none !important;
    animation: none !important;
  }
  .frame::before {
    animation: none !important;
    transform: none !important;
  }
  .pointer-glow,
  .pointer-ripple,
  .spark-layer,
  .scanline,
  .orbit-ring { display: none; }
}
</style>
