import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'
import { useDataStore } from './dataStore'

const STORAGE_KEY = 'OpenSEM:stats:v1'

export const useStatsStore = defineStore('stats', () => {
  const dataStore = useDataStore()
  const fitting = ref(false)
  const taskId = ref('')
  const taskProgress = ref(0)
  const taskMessage = ref('')
  const fitIndices = ref(null)
  const nUsed = ref(0)
  const estimates = ref([])
  const estimator = ref('ML')
  const missingStrategy = ref('listwise')
  // 用于判断“结果是否与当前语法一致”（避免语法改了却误导导出/解读）
  const lastFitSyntaxNorm = ref('')
  // 最近一次“成功估算”的时间戳（ISO 字符串），用于导出可追溯
  const lastFitAt = ref('')
  const error = ref(null)
  const errorHint = ref('')
  const errorCode = ref('')

  const bootstrapping = ref(false)
  const bootstrapTaskId = ref('')
  const bootstrapTaskProgress = ref(0)
  const bootstrapTaskMessage = ref('')
  const bootstrapResult = ref(null)
  const bootstrapError = ref(null)
  const bootstrapErrorHint = ref('')
  const bootstrapErrorCode = ref('')

  const moderationRunning = ref(false)
  const moderationTaskId = ref('')
  const moderationTaskProgress = ref(0)
  const moderationTaskMessage = ref('')
  const moderationResult = ref(null)
  const moderationError = ref(null)
  const moderationErrorHint = ref('')
  const moderationErrorCode = ref('')

  const moderatedMediationRunning = ref(false)
  const moderatedMediationTaskId = ref('')
  const moderatedMediationTaskProgress = ref(0)
  const moderatedMediationTaskMessage = ref('')
  const moderatedMediationResult = ref(null)
  const moderatedMediationError = ref(null)
  const moderatedMediationErrorHint = ref('')
  const moderatedMediationErrorCode = ref('')

  const latentInteractionRunning = ref(false)
  const latentInteractionTaskId = ref('')
  const latentInteractionTaskProgress = ref(0)
  const latentInteractionTaskMessage = ref('')
  const latentInteractionResult = ref(null)
  const latentInteractionError = ref(null)
  const latentInteractionErrorHint = ref('')
  const latentInteractionErrorCode = ref('')

  const invarianceRunning = ref(false)
  const invarianceTaskId = ref('')
  const invarianceTaskProgress = ref(0)
  const invarianceTaskMessage = ref('')
  const invarianceResult = ref(null)
  const invarianceError = ref(null)
  const invarianceErrorHint = ref('')
  const invarianceErrorCode = ref('')

  const invarianceSeriesRunning = ref(false)
  const invarianceSeriesTaskId = ref('')
  const invarianceSeriesTaskProgress = ref(0)
  const invarianceSeriesTaskMessage = ref('')
  const invarianceSeriesResult = ref(null)
  const invarianceSeriesError = ref(null)
  const invarianceSeriesErrorHint = ref('')
  const invarianceSeriesErrorCode = ref('')

  const modelCompareRunning = ref(false)
  const modelCompareTaskId = ref('')
  const modelCompareTaskProgress = ref(0)
  const modelCompareTaskMessage = ref('')
  const modelCompareResult = ref(null)
  const modelCompareError = ref(null)
  const modelCompareErrorHint = ref('')
  const modelCompareErrorCode = ref('')

  const mgaRunning = ref(false)
  const mgaTaskId = ref('')
  const mgaTaskProgress = ref(0)
  const mgaTaskMessage = ref('')
  const mgaResult = ref(null)
  const mgaError = ref(null)
  const mgaErrorHint = ref('')
  const mgaErrorCode = ref('')

  function _normalizeApiError(e, fallback) {
    const detail = e?.response?.data?.detail
    if (typeof detail === 'string') {
      return { code: '', message: detail, hint: '' }
    }
    if (detail && typeof detail === 'object') {
      return {
        code: String(detail.code || '').trim(),
        message: String(detail.message || '').trim() || (fallback || ''),
        hint: String(detail.hint || '').trim(),
      }
    }
    return { code: '', message: e?.message || fallback || '', hint: '' }
  }

  /** 解析 Celery 轮询结果中的 error / error_detail，避免把 Traceback 直出到 UI */
  function _taskFailureToError(finalStatus, defaultMsg) {
    const d = finalStatus?.error_detail
    if (d && typeof d === 'object') {
      return {
        code: String(d.code || '').trim() || 'TASK_FAILED',
        message: String(d.message || finalStatus?.error || '').trim() || defaultMsg,
        hint: String(d.hint || '').trim(),
      }
    }
    const raw = String(finalStatus?.error || '')
    if (!raw) {
      return { code: '', message: defaultMsg, hint: '' }
    }
    if (raw.length > 600 || raw.includes('Traceback') || raw.includes('File "')) {
      return {
        code: 'TASK_FAILED',
        message: defaultMsg,
        hint: '任务返回了技术性错误信息，界面未完整展示。请检查变量名、缺失值与模型设定后重试。',
      }
    }
    return { code: '', message: raw, hint: '' }
  }

  function _isDataKeyInvalid(err) {
    const code = String(err?.code || '').trim()
    const msg = String(err?.message || '').trim()
    return code === 'DATA_KEY_INVALID' || msg.includes('data_key 无效')
  }

  function _normalizeInvarianceSeriesResult(raw) {
    const r = raw && typeof raw === 'object' ? raw : {}
    const mode = String(r.mode || '').trim() || (r.supported === false ? 'degraded' : 'lavaan')
    const supported = typeof r.supported === 'boolean' ? r.supported : mode !== 'degraded'
    const message =
      String(r.message || '').trim() ||
      (supported ? '' : '当前环境未启用 lavaan：不变性序列已降级/不可用，可改用“多群组(配置)”方案。')

    const rawModels = Array.isArray(r.models) ? r.models : []
    const rawComparisons = Array.isArray(r.comparisons) ? r.comparisons : []

    const MODEL_ORDER = ['configural', 'metric', 'scalar', 'strict']
    const COMP_ORDER = [
      { from: 'configural', to: 'metric' },
      { from: 'metric', to: 'scalar' },
      { from: 'scalar', to: 'strict' },
    ]

    const modelByName = new Map()
    for (const m of rawModels) {
      const name = String(m?.model || '').trim()
      if (!name) continue
      if (!modelByName.has(name)) modelByName.set(name, m)
    }

    function _emptyFit() {
      return { chi2: null, df: null, cfi: null, tli: null, rmsea: null, srmr: null }
    }

    const models = MODEL_ORDER.map((name) => {
      const m = modelByName.get(name) || {}
      const fit = m?.fit && typeof m.fit === 'object' ? m.fit : {}
      return {
        model: name,
        group_equal: Array.isArray(m.group_equal) ? m.group_equal : m.group_equal ?? [],
        fit: { ..._emptyFit(), ...fit },
        converged: m.converged ?? null,
        n_groups: m.n_groups ?? null,
        n_used: m.n_used ?? null,
      }
    })

    const compByKey = new Map()
    for (const c of rawComparisons) {
      const from = String(c?.from || '').trim()
      const to = String(c?.to || '').trim()
      if (!from || !to) continue
      const key = `${from}::${to}`
      if (!compByKey.has(key)) compByKey.set(key, c)
    }

    const comparisons = COMP_ORDER.map(({ from, to }) => {
      const c = compByKey.get(`${from}::${to}`) || {}
      return {
        from,
        to,
        ok: typeof c.ok === 'boolean' ? c.ok : null,
        chi2_diff: c.chi2_diff ?? null,
        df_diff: c.df_diff ?? null,
        p_value: c.p_value ?? null,
        delta_cfi: c.delta_cfi ?? null,
        delta_rmsea: c.delta_rmsea ?? null,
        note: c.note ?? null,
      }
    })

    return {
      ...r,
      supported,
      mode,
      message,
      models,
      comparisons,
    }
  }

  function savePersisted() {
    const payload = {
      fitIndices: fitIndices.value,
      nUsed: nUsed.value,
      estimates: estimates.value,
      estimator: estimator.value,
      missingStrategy: missingStrategy.value,
      lastFitSyntaxNorm: lastFitSyntaxNorm.value,
      lastFitAt: lastFitAt.value,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  }

  function loadPersisted() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return
      const d = JSON.parse(raw)
      fitIndices.value = d.fitIndices || null
      nUsed.value = d.nUsed || 0
      estimates.value = Array.isArray(d.estimates) ? d.estimates : []
      estimator.value = d.estimator || 'ML'
      missingStrategy.value = d.missingStrategy || 'listwise'
      lastFitSyntaxNorm.value = d.lastFitSyntaxNorm || ''
      lastFitAt.value = d.lastFitAt || ''
    } catch (_) {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  function _normalizeSyntax(s) {
    return String(s || '')
      .split('\n')
      .map((row) => row.trim())
      .filter(Boolean)
      .join('\n')
  }

  async function fitModel(payload) {
    fitting.value = true
    error.value = null
    errorHint.value = ''
    errorCode.value = ''
    taskId.value = ''
    taskProgress.value = 0
    taskMessage.value = ''
    try {
      const { data } = await api.post('/api/v1/stats/fit', payload)
      fitIndices.value = data.fit_indices || null
      nUsed.value = data.n_used || 0
      estimates.value = data.estimates || []
      estimator.value = data.estimator || payload?.estimator || 'ML'
      missingStrategy.value = data.missing_strategy || payload?.missing_strategy || 'listwise'
      lastFitSyntaxNorm.value = _normalizeSyntax(payload?.lavaan_syntax || '')
      lastFitAt.value = new Date().toISOString()
      savePersisted()
      return data
    } catch (e) {
      const err = _normalizeApiError(e, '模型估算失败')
      error.value = err.message || error.value || '模型估算失败'
      errorHint.value = err.hint || errorHint.value
      errorCode.value = err.code || errorCode.value
      if (_isDataKeyInvalid(err)) {
        dataStore.clearData()
        clearFitResult()
        error.value = '当前数据会话已过期，请先重新上传数据再估算。'
        errorHint.value = '提示：重新上传后会生成新的 data_key，旧的将不可用于后续估算/导出。'
        errorCode.value = 'DATA_KEY_INVALID'
        throw e
      }
      throw e
    } finally {
      fitting.value = false
    }
  }

  function _sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms))
  }

  async function _pollTask(id, { intervalMs = 900, timeoutMs = 120000, onUpdate } = {}) {
    const startedAt = Date.now()
    while (true) {
      if (!id) throw new Error('task_id 为空')
      if (Date.now() - startedAt > timeoutMs) throw new Error('任务超时，请稍后重试')
      const { data } = await api.get(`/api/v1/tasks/status/${id}`)
      if (typeof onUpdate === 'function') onUpdate(data)

      if (data.ready) return data
      await _sleep(intervalMs)
    }
  }

  async function fitModelAsync(payload) {
    fitting.value = true
    error.value = null
    errorHint.value = ''
    errorCode.value = ''
    taskId.value = ''
    taskProgress.value = 0
    taskMessage.value = '已提交任务，等待执行…'
    try {
      const submit = await api.post('/api/v1/tasks/stats-fit', payload)
      const id = submit.data?.task_id || ''
      taskId.value = id
      if (!id) throw new Error('任务提交失败：未返回 task_id')

      const finalStatus = await _pollTask(id, {
        onUpdate: (data) => {
          taskProgress.value = typeof data.progress === 'number' ? data.progress : taskProgress.value
          taskMessage.value = data.message || taskMessage.value || ''
        },
      })
      if (finalStatus.successful && finalStatus.result?.success) {
        const data = finalStatus.result
        fitIndices.value = data.fit_indices || null
        nUsed.value = data.n_used || 0
        estimates.value = data.estimates || []
        estimator.value = data.estimator || payload?.estimator || 'ML'
        missingStrategy.value = data.missing_strategy || payload?.missing_strategy || 'listwise'
        lastFitSyntaxNorm.value = _normalizeSyntax(payload?.lavaan_syntax || '')
        lastFitAt.value = new Date().toISOString()
        taskProgress.value = 100
        taskMessage.value = '完成'
        savePersisted()
        return data
      }

      const tf = _taskFailureToError(finalStatus, '模型估算失败')
      if (_isDataKeyInvalid(tf)) {
        dataStore.clearData()
        clearFitResult()
        error.value = '当前数据会话已过期，请先重新上传数据再估算。'
        errorHint.value = '提示：重新上传后会生成新的 data_key，旧的将不可用于后续估算/导出。'
        errorCode.value = 'DATA_KEY_INVALID'
        throw new Error(tf.message)
      }
      error.value = tf.message
      errorHint.value = tf.hint
      errorCode.value = tf.code
      throw new Error(tf.message)
    } catch (e) {
      const err = _normalizeApiError(e, '模型估算失败')
      error.value = err.message || error.value || '模型估算失败'
      errorHint.value = err.hint || errorHint.value
      errorCode.value = err.code || errorCode.value
      if (_isDataKeyInvalid(err)) {
        dataStore.clearData()
        clearFitResult()
        error.value = '当前数据会话已过期，请先重新上传数据再估算。'
        errorHint.value = '提示：重新上传后会生成新的 data_key，旧的将不可用于后续估算/导出。'
        errorCode.value = 'DATA_KEY_INVALID'
        throw e
      }
      throw e
    } finally {
      fitting.value = false
    }
  }

  async function runBootstrapMediationAsync(payload) {
    bootstrapping.value = true
    bootstrapError.value = null
    bootstrapErrorHint.value = ''
    bootstrapErrorCode.value = ''
    bootstrapTaskId.value = ''
    bootstrapTaskProgress.value = 0
    bootstrapTaskMessage.value = '已提交任务，等待执行…'
    bootstrapResult.value = null
    try {
      const submit = await api.post('/api/v1/tasks/bootstrap-mediation', payload)
      const id = submit.data?.task_id || ''
      bootstrapTaskId.value = id
      if (!id) throw new Error('任务提交失败：未返回 task_id')

      const finalStatus = await _pollTask(id, {
        timeoutMs: 10 * 60 * 1000,
        onUpdate: (data) => {
          bootstrapTaskProgress.value =
            typeof data.progress === 'number' ? data.progress : bootstrapTaskProgress.value
          bootstrapTaskMessage.value = data.message || bootstrapTaskMessage.value || ''
        },
      })
      if (finalStatus.successful && finalStatus.result?.success) {
        bootstrapTaskProgress.value = 100
        bootstrapTaskMessage.value = '完成'
        bootstrapResult.value = finalStatus.result
        return finalStatus.result
      }
      const tf = _taskFailureToError(finalStatus, 'Bootstrap 失败')
      bootstrapError.value = tf.message
      bootstrapErrorHint.value = tf.hint
      bootstrapErrorCode.value = tf.code
      throw new Error(tf.message)
    } catch (e) {
      const err = _normalizeApiError(e, 'Bootstrap 失败')
      bootstrapError.value = err.message || bootstrapError.value || 'Bootstrap 失败'
      bootstrapErrorHint.value = err.hint || bootstrapErrorHint.value
      bootstrapErrorCode.value = err.code || bootstrapErrorCode.value
      throw e
    } finally {
      bootstrapping.value = false
    }
  }

  async function runInvarianceConfiguralAsync(payload) {
    invarianceRunning.value = true
    invarianceError.value = null
    invarianceErrorHint.value = ''
    invarianceErrorCode.value = ''
    invarianceTaskId.value = ''
    invarianceTaskProgress.value = 0
    invarianceTaskMessage.value = '已提交任务，等待执行…'
    invarianceResult.value = null
    try {
      const submit = await api.post('/api/v1/tasks/invariance-configural', payload)
      const id = submit.data?.task_id || ''
      invarianceTaskId.value = id
      if (!id) throw new Error('任务提交失败：未返回 task_id')

      const finalStatus = await _pollTask(id, {
        timeoutMs: 10 * 60 * 1000,
        onUpdate: (data) => {
          invarianceTaskProgress.value =
            typeof data.progress === 'number' ? data.progress : invarianceTaskProgress.value
          invarianceTaskMessage.value = data.message || invarianceTaskMessage.value || ''
        },
      })
      if (finalStatus.successful && finalStatus.result?.success) {
        invarianceTaskProgress.value = 100
        invarianceTaskMessage.value = '完成'
        invarianceResult.value = finalStatus.result
        return finalStatus.result
      }
      const tf = _taskFailureToError(finalStatus, '多群组拟合失败')
      invarianceError.value = tf.message
      invarianceErrorHint.value = tf.hint
      invarianceErrorCode.value = tf.code
      throw new Error(tf.message)
    } catch (e) {
      const err = _normalizeApiError(e, '多群组拟合失败')
      invarianceError.value = err.message || invarianceError.value || '多群组拟合失败'
      invarianceErrorHint.value = err.hint || invarianceErrorHint.value
      invarianceErrorCode.value = err.code || invarianceErrorCode.value
      throw e
    } finally {
      invarianceRunning.value = false
    }
  }

  async function runModerationAnalysisAsync(payload) {
    moderationRunning.value = true
    moderationError.value = null
    moderationErrorHint.value = ''
    moderationErrorCode.value = ''
    moderationTaskId.value = ''
    moderationTaskProgress.value = 0
    moderationTaskMessage.value = '已提交任务，等待执行…'
    moderationResult.value = null
    try {
      const submit = await api.post('/api/v1/tasks/moderation-analysis', payload)
      const id = submit.data?.task_id || ''
      moderationTaskId.value = id
      if (!id) throw new Error('任务提交失败：未返回 task_id')

      const finalStatus = await _pollTask(id, {
        timeoutMs: 10 * 60 * 1000,
        onUpdate: (data) => {
          moderationTaskProgress.value =
            typeof data.progress === 'number' ? data.progress : moderationTaskProgress.value
          moderationTaskMessage.value = data.message || moderationTaskMessage.value || ''
        },
      })
      if (finalStatus.successful && finalStatus.result?.success) {
        moderationTaskProgress.value = 100
        moderationTaskMessage.value = '完成'
        moderationResult.value = finalStatus.result
        return finalStatus.result
      }
      const tf = _taskFailureToError(finalStatus, '调节分析失败')
      moderationError.value = tf.message
      moderationErrorHint.value = tf.hint
      moderationErrorCode.value = tf.code
      throw new Error(tf.message)
    } catch (e) {
      const err = _normalizeApiError(e, '调节分析失败')
      moderationError.value = err.message || moderationError.value || '调节分析失败'
      moderationErrorHint.value = err.hint || moderationErrorHint.value
      moderationErrorCode.value = err.code || moderationErrorCode.value
      throw e
    } finally {
      moderationRunning.value = false
    }
  }

  async function runModeratedMediationAsync(payload) {
    moderatedMediationRunning.value = true
    moderatedMediationError.value = null
    moderatedMediationErrorHint.value = ''
    moderatedMediationErrorCode.value = ''
    moderatedMediationTaskId.value = ''
    moderatedMediationTaskProgress.value = 0
    moderatedMediationTaskMessage.value = '已提交任务，等待执行…'
    moderatedMediationResult.value = null
    try {
      const submit = await api.post('/api/v1/tasks/moderated-mediation', payload)
      const id = submit.data?.task_id || ''
      moderatedMediationTaskId.value = id
      if (!id) throw new Error('任务提交失败：未返回 task_id')

      const finalStatus = await _pollTask(id, {
        timeoutMs: 10 * 60 * 1000,
        onUpdate: (data) => {
          moderatedMediationTaskProgress.value =
            typeof data.progress === 'number' ? data.progress : moderatedMediationTaskProgress.value
          moderatedMediationTaskMessage.value = data.message || moderatedMediationTaskMessage.value || ''
        },
      })
      if (finalStatus.successful && finalStatus.result?.success) {
        moderatedMediationTaskProgress.value = 100
        moderatedMediationTaskMessage.value = '完成'
        moderatedMediationResult.value = finalStatus.result
        return finalStatus.result
      }
      const tf = _taskFailureToError(finalStatus, '有调节的中介分析失败')
      moderatedMediationError.value = tf.message
      moderatedMediationErrorHint.value = tf.hint
      moderatedMediationErrorCode.value = tf.code
      throw new Error(tf.message)
    } catch (e) {
      const err = _normalizeApiError(e, '有调节的中介分析失败')
      moderatedMediationError.value = err.message || moderatedMediationError.value || '有调节的中介分析失败'
      moderatedMediationErrorHint.value = err.hint || moderatedMediationErrorHint.value
      moderatedMediationErrorCode.value = err.code || moderatedMediationErrorCode.value
      throw e
    } finally {
      moderatedMediationRunning.value = false
    }
  }

  async function runLatentInteractionProbeAsync(payload) {
    latentInteractionRunning.value = true
    latentInteractionError.value = null
    latentInteractionErrorHint.value = ''
    latentInteractionErrorCode.value = ''
    latentInteractionTaskId.value = ''
    latentInteractionTaskProgress.value = 0
    latentInteractionTaskMessage.value = '已提交任务，等待执行…'
    latentInteractionResult.value = null
    try {
      const submit = await api.post('/api/v1/tasks/latent-interaction-probe', payload)
      const id = submit.data?.task_id || ''
      latentInteractionTaskId.value = id
      if (!id) throw new Error('任务提交失败：未返回 task_id')

      const finalStatus = await _pollTask(id, {
        timeoutMs: 5 * 60 * 1000,
        onUpdate: (data) => {
          latentInteractionTaskProgress.value =
            typeof data.progress === 'number' ? data.progress : latentInteractionTaskProgress.value
          latentInteractionTaskMessage.value = data.message || latentInteractionTaskMessage.value || ''
        },
      })
      if (finalStatus.successful && finalStatus.result?.success) {
        latentInteractionTaskProgress.value = 100
        latentInteractionTaskMessage.value = '完成'
        latentInteractionResult.value = finalStatus.result
        return finalStatus.result
      }
      const tf = _taskFailureToError(finalStatus, '潜变量交互探测失败')
      latentInteractionError.value = tf.message
      latentInteractionErrorHint.value = tf.hint
      latentInteractionErrorCode.value = tf.code
      throw new Error(tf.message)
    } catch (e) {
      const err = _normalizeApiError(e, '潜变量交互探测失败')
      latentInteractionError.value = err.message || latentInteractionError.value || '潜变量交互探测失败'
      latentInteractionErrorHint.value = err.hint || latentInteractionErrorHint.value
      latentInteractionErrorCode.value = err.code || latentInteractionErrorCode.value
      throw e
    } finally {
      latentInteractionRunning.value = false
    }
  }

  async function runInvarianceLavaanSeriesAsync(payload) {
    invarianceSeriesRunning.value = true
    invarianceSeriesError.value = null
    invarianceSeriesErrorHint.value = ''
    invarianceSeriesErrorCode.value = ''
    invarianceSeriesTaskId.value = ''
    invarianceSeriesTaskProgress.value = 0
    invarianceSeriesTaskMessage.value = '已提交任务，等待执行…'
    invarianceSeriesResult.value = null
    try {
      const submit = await api.post('/api/v1/tasks/invariance-lavaan-series', payload)
      const id = submit.data?.task_id || ''
      invarianceSeriesTaskId.value = id
      if (!id) throw new Error('任务提交失败：未返回 task_id')

      const finalStatus = await _pollTask(id, {
        timeoutMs: 10 * 60 * 1000,
        onUpdate: (data) => {
          invarianceSeriesTaskProgress.value =
            typeof data.progress === 'number' ? data.progress : invarianceSeriesTaskProgress.value
          invarianceSeriesTaskMessage.value = data.message || invarianceSeriesTaskMessage.value || ''
        },
      })
      if (finalStatus.successful && finalStatus.result?.success) {
        invarianceSeriesTaskProgress.value = 100
        invarianceSeriesTaskMessage.value = '完成'
        // 统一契约：保证 supported/mode/message/models/comparisons 形状稳定
        invarianceSeriesResult.value = _normalizeInvarianceSeriesResult(finalStatus.result)
        return invarianceSeriesResult.value
      }
      const tf = _taskFailureToError(finalStatus, '不变性序列检验失败')
      invarianceSeriesError.value = tf.message
      invarianceSeriesErrorHint.value = tf.hint
      invarianceSeriesErrorCode.value = tf.code
      throw new Error(tf.message)
    } catch (e) {
      const err = _normalizeApiError(e, '不变性序列检验失败')
      invarianceSeriesError.value = err.message || invarianceSeriesError.value || '不变性序列检验失败'
      invarianceSeriesErrorHint.value = err.hint || invarianceSeriesErrorHint.value
      invarianceSeriesErrorCode.value = err.code || invarianceSeriesErrorCode.value
      invarianceSeriesResult.value = _normalizeInvarianceSeriesResult({
        success: false,
        task: 'invariance_lavaan_series',
        supported: false,
        mode: 'degraded',
        message: invarianceSeriesError.value,
        models: [],
        comparisons: [],
      })
      throw e
    } finally {
      invarianceSeriesRunning.value = false
    }
  }

  async function runModelCompareAsync(payload) {
    modelCompareRunning.value = true
    modelCompareError.value = null
    modelCompareErrorHint.value = ''
    modelCompareErrorCode.value = ''
    modelCompareTaskId.value = ''
    modelCompareTaskProgress.value = 0
    modelCompareTaskMessage.value = '已提交任务，等待执行…'
    modelCompareResult.value = null
    try {
      const submit = await api.post('/api/v1/tasks/model-compare', payload)
      const id = submit.data?.task_id || ''
      modelCompareTaskId.value = id
      if (!id) throw new Error('任务提交失败：未返回 task_id')

      const finalStatus = await _pollTask(id, {
        timeoutMs: 10 * 60 * 1000,
        onUpdate: (data) => {
          modelCompareTaskProgress.value =
            typeof data.progress === 'number' ? data.progress : modelCompareTaskProgress.value
          modelCompareTaskMessage.value = data.message || modelCompareTaskMessage.value || ''
        },
      })

      if (finalStatus.successful && finalStatus.result?.success) {
        modelCompareTaskProgress.value = 100
        modelCompareTaskMessage.value = '完成'
        modelCompareResult.value = finalStatus.result
        return finalStatus.result
      }
      const tf = _taskFailureToError(finalStatus, '模型比较失败')
      modelCompareError.value = tf.message
      modelCompareErrorHint.value = tf.hint
      modelCompareErrorCode.value = tf.code
      throw new Error(tf.message)
    } catch (e) {
      const err = _normalizeApiError(e, '模型比较失败')
      modelCompareError.value = err.message || modelCompareError.value || '模型比较失败'
      modelCompareErrorHint.value = err.hint || modelCompareErrorHint.value
      modelCompareErrorCode.value = err.code || modelCompareErrorCode.value
      throw e
    } finally {
      modelCompareRunning.value = false
    }
  }

  async function runMgaStructuralPathCompareAsync(payload) {
    mgaRunning.value = true
    mgaError.value = null
    mgaErrorHint.value = ''
    mgaErrorCode.value = ''
    mgaTaskId.value = ''
    mgaTaskProgress.value = 0
    mgaTaskMessage.value = '已提交任务，等待执行…'
    mgaResult.value = null
    try {
      const submit = await api.post('/api/v1/tasks/mga-structural-path-compare', payload)
      const id = submit.data?.task_id || ''
      mgaTaskId.value = id
      if (!id) throw new Error('任务提交失败：未返回 task_id')

      const finalStatus = await _pollTask(id, {
        timeoutMs: 10 * 60 * 1000,
        onUpdate: (data) => {
          mgaTaskProgress.value = typeof data.progress === 'number' ? data.progress : mgaTaskProgress.value
          mgaTaskMessage.value = data.message || mgaTaskMessage.value || ''
        },
      })
      if (finalStatus.successful && finalStatus.result?.success) {
        mgaTaskProgress.value = 100
        mgaTaskMessage.value = '完成'
        mgaResult.value = finalStatus.result
        return finalStatus.result
      }
      const tf = _taskFailureToError(finalStatus, 'MGA 结构路径比较失败')
      mgaError.value = tf.message
      mgaErrorHint.value = tf.hint
      mgaErrorCode.value = tf.code
      throw new Error(tf.message)
    } catch (e) {
      const err = _normalizeApiError(e, 'MGA 结构路径比较失败')
      mgaError.value = err.message || mgaError.value || 'MGA 结构路径比较失败'
      mgaErrorHint.value = err.hint || mgaErrorHint.value
      mgaErrorCode.value = err.code || mgaErrorCode.value
      throw e
    } finally {
      mgaRunning.value = false
    }
  }

  function clearFitResult() {
    fitIndices.value = null
    nUsed.value = 0
    estimates.value = []
    error.value = null
    errorHint.value = ''
    errorCode.value = ''
    taskId.value = ''
    taskProgress.value = 0
    taskMessage.value = ''
    lastFitSyntaxNorm.value = ''
    lastFitAt.value = ''
    savePersisted()
  }

  function clearAllResults() {
    clearFitResult()

    bootstrapping.value = false
    bootstrapTaskId.value = ''
    bootstrapTaskProgress.value = 0
    bootstrapTaskMessage.value = ''
    bootstrapResult.value = null
    bootstrapError.value = null
    bootstrapErrorHint.value = ''
    bootstrapErrorCode.value = ''

    moderationRunning.value = false
    moderationTaskId.value = ''
    moderationTaskProgress.value = 0
    moderationTaskMessage.value = ''
    moderationResult.value = null
    moderationError.value = null
    moderationErrorHint.value = ''
    moderationErrorCode.value = ''

    moderatedMediationRunning.value = false
    moderatedMediationTaskId.value = ''
    moderatedMediationTaskProgress.value = 0
    moderatedMediationTaskMessage.value = ''
    moderatedMediationResult.value = null
    moderatedMediationError.value = null
    moderatedMediationErrorHint.value = ''
    moderatedMediationErrorCode.value = ''

    latentInteractionRunning.value = false
    latentInteractionTaskId.value = ''
    latentInteractionTaskProgress.value = 0
    latentInteractionTaskMessage.value = ''
    latentInteractionResult.value = null
    latentInteractionError.value = null
    latentInteractionErrorHint.value = ''
    latentInteractionErrorCode.value = ''

    invarianceRunning.value = false
    invarianceTaskId.value = ''
    invarianceTaskProgress.value = 0
    invarianceTaskMessage.value = ''
    invarianceResult.value = null
    invarianceError.value = null
    invarianceErrorHint.value = ''
    invarianceErrorCode.value = ''

    invarianceSeriesRunning.value = false
    invarianceSeriesTaskId.value = ''
    invarianceSeriesTaskProgress.value = 0
    invarianceSeriesTaskMessage.value = ''
    invarianceSeriesResult.value = null
    invarianceSeriesError.value = null
    invarianceSeriesErrorHint.value = ''
    invarianceSeriesErrorCode.value = ''

    modelCompareRunning.value = false
    modelCompareTaskId.value = ''
    modelCompareTaskProgress.value = 0
    modelCompareTaskMessage.value = ''
    modelCompareResult.value = null
    modelCompareError.value = null
    modelCompareErrorHint.value = ''
    modelCompareErrorCode.value = ''

    mgaRunning.value = false
    mgaTaskId.value = ''
    mgaTaskProgress.value = 0
    mgaTaskMessage.value = ''
    mgaResult.value = null
    mgaError.value = null
    mgaErrorHint.value = ''
    mgaErrorCode.value = ''
  }

  loadPersisted()

  return {
    fitting,
    taskId,
    taskProgress,
    taskMessage,
    fitIndices,
    nUsed,
    estimates,
    estimator,
    missingStrategy,
    lastFitSyntaxNorm,
    lastFitAt,
    error,
    errorHint,
    errorCode,
    fitModel,
    fitModelAsync,
    clearFitResult,
    clearAllResults,

    bootstrapping,
    bootstrapTaskId,
    bootstrapTaskProgress,
    bootstrapTaskMessage,
    bootstrapResult,
    bootstrapError,
    bootstrapErrorHint,
    bootstrapErrorCode,
    runBootstrapMediationAsync,

    moderationRunning,
    moderationTaskId,
    moderationTaskProgress,
    moderationTaskMessage,
    moderationResult,
    moderationError,
    moderationErrorHint,
    moderationErrorCode,
    runModerationAnalysisAsync,

    moderatedMediationRunning,
    moderatedMediationTaskId,
    moderatedMediationTaskProgress,
    moderatedMediationTaskMessage,
    moderatedMediationResult,
    moderatedMediationError,
    moderatedMediationErrorHint,
    moderatedMediationErrorCode,
    runModeratedMediationAsync,

    latentInteractionRunning,
    latentInteractionTaskId,
    latentInteractionTaskProgress,
    latentInteractionTaskMessage,
    latentInteractionResult,
    latentInteractionError,
    latentInteractionErrorHint,
    latentInteractionErrorCode,
    runLatentInteractionProbeAsync,

    invarianceRunning,
    invarianceTaskId,
    invarianceTaskProgress,
    invarianceTaskMessage,
    invarianceResult,
    invarianceError,
    invarianceErrorHint,
    invarianceErrorCode,
    runInvarianceConfiguralAsync,

    invarianceSeriesRunning,
    invarianceSeriesTaskId,
    invarianceSeriesTaskProgress,
    invarianceSeriesTaskMessage,
    invarianceSeriesResult,
    invarianceSeriesError,
    invarianceSeriesErrorHint,
    invarianceSeriesErrorCode,
    runInvarianceLavaanSeriesAsync,

    modelCompareRunning,
    modelCompareTaskId,
    modelCompareTaskProgress,
    modelCompareTaskMessage,
    modelCompareResult,
    modelCompareError,
    modelCompareErrorHint,
    modelCompareErrorCode,
    runModelCompareAsync,

    mgaRunning,
    mgaTaskId,
    mgaTaskProgress,
    mgaTaskMessage,
    mgaResult,
    mgaError,
    mgaErrorHint,
    mgaErrorCode,
    runMgaStructuralPathCompareAsync,
  }
})
