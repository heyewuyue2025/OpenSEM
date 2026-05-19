import axios from 'axios'
import { normalizeApiError } from '../utils/errorPresenter'

export const api = axios.create({
  baseURL: '',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// FormData 上传时由浏览器自动设置 Content-Type（含 boundary）
api.interceptors.request.use((config) => {
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    error._normalized = normalizeApiError(error, '请求失败')
    return Promise.reject(error)
  }
)
