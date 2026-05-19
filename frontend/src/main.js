import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'
import './styles/opensem-buttons.css'
import './styles/opensem-inputs.css'
import './styles/opensem-notice.css'
import './styles/opensem-dialog.css'
import './styles/opensem-app-chrome.css'
import './styles/opensem-feedback.css'
import './styles/opensem-theme-base.css'
import './styles/opensem-core-layout.css'
import './styles/opensem-core-responsive.css'
import './styles/opensem-results-dense.css'
import { useNoticeStore } from './stores/noticeStore'
import { joinErrorMessage } from './utils/errorPresenter'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)

app.config.errorHandler = (err, instance, info) => {
  const noticeStore = useNoticeStore(pinia)
  noticeStore.push({
    type: 'error',
    title: '界面异常',
    message: `${joinErrorMessage(err, '页面运行时发生异常')} (${String(info || 'unknown')})`,
    timeoutMs: 6500,
  })
  console.error(err, instance, info)
}

window.addEventListener('unhandledrejection', (event) => {
  const noticeStore = useNoticeStore(pinia)
  noticeStore.push({
    type: 'error',
    title: '异步任务异常',
    message: joinErrorMessage(event?.reason, '未处理的异步错误'),
    timeoutMs: 6500,
  })
})

window.addEventListener('error', (event) => {
  if (!event?.error) return
  const noticeStore = useNoticeStore(pinia)
  noticeStore.push({
    type: 'error',
    title: '全局错误',
    message: joinErrorMessage(event.error, '页面发生错误'),
    timeoutMs: 6500,
  })
})

app.mount('#app')
