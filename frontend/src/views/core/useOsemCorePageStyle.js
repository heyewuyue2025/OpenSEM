import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { toCorePageStyleVars } from './corePageRhythm'
import { resolveCorePageRhythmForViewport } from './corePageViewportRhythm'
import { resolveCoreOuterPad } from '../../ui/appChromeRhythm'

const MQ_NARROW = '(max-width: 767.98px)'
const MQ_TABLET = '(min-width: 768px) and (max-width: 1023.98px)'

function outerPagePadVars({ isNarrow, isTablet }) {
  const pad = resolveCoreOuterPad({ isNarrow, isTablet })
  if (pad) {
    return { '--osem-core-outer-pad': pad }
  }
  return {}
}

/**
 * 数据页 / 建模页：将 core 节奏 token 以 CSS 变量注入根节点，并随视口（375 / 768 档）细调节间距与页边白。
 * @param {'data' | 'model'} pageKey
 */
export function useOsemCorePageStyle(pageKey) {
  const isNarrow = ref(
    typeof window !== 'undefined' && window.matchMedia && window.matchMedia(MQ_NARROW).matches
  )
  const isTablet = ref(
    typeof window !== 'undefined' && window.matchMedia && window.matchMedia(MQ_TABLET).matches
  )
  const corePageStyle = computed(() => {
    const v = { isNarrow: isNarrow.value, isTablet: isTablet.value }
    const rhythm = resolveCorePageRhythmForViewport(pageKey, v)
    return {
      ...toCorePageStyleVars(rhythm),
      ...outerPagePadVars(v),
    }
  })

  let mqN = null
  let mqT = null
  const onMqChange = () => {
    if (!mqN || !mqT) return
    isNarrow.value = mqN.matches
    isTablet.value = mqT.matches
  }

  onMounted(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return
    mqN = window.matchMedia(MQ_NARROW)
    mqT = window.matchMedia(MQ_TABLET)
    onMqChange()
    mqN.addEventListener('change', onMqChange)
    mqT.addEventListener('change', onMqChange)
  })

  onBeforeUnmount(() => {
    if (mqN) mqN.removeEventListener('change', onMqChange)
    if (mqT) mqT.removeEventListener('change', onMqChange)
  })

  return { corePageStyle }
}
