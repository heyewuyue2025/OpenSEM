<template>
  <div
    class="results-view osem-core-page"
    :class="DENSE.rootModifier"
    :style="resultsPageStyle"
  >
    <div class="view-layout">
      <main class="main-col">
        <section class="section reveal" :style="{ transitionDelay: '0ms' }">
          <h3 class="section-label">FIT INDICES / 拟合度指标</h3>
          <div class="section-rule"></div>
          <p class="osem-core-intro">先确认模型匹配情况，再查看参数与路径结论，可降低误读风险。</p>
          <p v-if="isFitStale" class="fit-stale">
            检测到 lavaan 语法已变更：当前拟合度/参数表可能对应旧版本。请重新运行一次估算后再解读或导出。
            <span class="fit-stale-meta">
              语法版本：当前 {{ currentSyntaxTag }} · 上次估算 {{ lastFitSyntaxTag }} · 上次估算时间 {{ lastFitAtText }}
            </span>
          </p>
          <div class="action-row">
            <button :class="BTN.primary" :disabled="statsStore.fitting || !canFit" @click="runFit">
              {{ statsStore.fitting ? `估算中…${statsStore.taskProgress || 0}%` : '运行估算' }}
            </button>
            <button
              v-if="isFitStale && canFit"
              :class="BTN.secondaryAccent"
              :disabled="statsStore.fitting"
              @click="refitWithConfirm"
            >
              重新估算（沿用当前设置）
            </button>
            <button
              v-if="isFitStale && statsStore.fitIndices"
              :class="BTN.secondaryMuted"
              :disabled="statsStore.fitting"
              @click="clearOldResultsWithConfirm"
            >
              清空旧结果
            </button>
            <button
              v-if="canFit"
              :class="BTN.secondaryMuted"
              :disabled="statsStore.fitting"
              @click="copyText(`syntax:${currentSyntaxTag}`, '已复制语法版本号')"
            >
              复制语法版本号
            </button>
            <span v-if="statsStore.fitting && statsStore.taskMessage" class="used-n">{{ statsStore.taskMessage }}</span>
            <span v-if="statsStore.fitIndices" class="used-n">有效样本 N = {{ statsStore.nUsed }}</span>
          </div>
          <div v-if="fitStatusFeedback" :class="[FEEDBACK.base, resolveFeedbackTone(fitStatusFeedback.kind)]">
            <p :class="FEEDBACK.text">{{ fitStatusFeedback.text }}</p>
            <p :class="FEEDBACK.detail">{{ fitStatusFeedback.detail }}</p>
          </div>

          <div class="config-row">
            <div class="config-item">
              <label class="config-label osem-field-label">估计方法</label>
              <select v-model="localEstimator" :class="INP.select" :disabled="statsStore.fitting">
                <option value="ML">ML</option>
                <option value="GLS">GLS</option>
              </select>
            </div>
            <div class="config-item">
              <label class="config-label osem-field-label">缺失处理</label>
              <select v-model="localMissingStrategy" :class="INP.select" :disabled="statsStore.fitting">
                <option value="listwise">列表删除</option>
                <option value="fiml">FIML</option>
                <option value="mean_impute">均值插补</option>
              </select>
            </div>
          </div>

          <div class="fit-preview">
            <div class="fit-item">
              <span class="fit-value">{{ metric('chi2_df') }}</span>
              <span class="fit-label">χ²/df <TermTip term="chi2_df" /></span>
              <span class="fit-explain">{{ explainMetric('chi2_df') }}</span>
            </div>
            <div class="fit-item">
              <span class="fit-value">{{ metric('rmsea') }}</span>
              <span class="fit-label">RMSEA <TermTip term="rmsea" /></span>
              <span class="fit-explain">{{ explainMetric('rmsea') }}</span>
            </div>
            <div class="fit-item">
              <span class="fit-value">{{ metric('cfi') }}</span>
              <span class="fit-label">CFI <TermTip term="cfi" /></span>
              <span class="fit-explain">{{ explainMetric('cfi') }}</span>
            </div>
            <div class="fit-item">
              <span class="fit-value">{{ metric('tli') }}</span>
              <span class="fit-label">TLI <TermTip term="tli" /></span>
              <span class="fit-explain">{{ explainMetric('tli') }}</span>
            </div>
            <div class="fit-item">
              <span class="fit-value">{{ metric('srmr') }}</span>
              <span class="fit-label">SRMR <TermTip term="srmr" /></span>
              <span class="fit-explain">{{ explainMetric('srmr') }}</span>
            </div>
          </div>
          <p v-if="statsStore.fitIndices" class="status-text" :class="`status-${statsStore.fitIndices.status}`">
            {{ statusText }}
          </p>
        </section>

        <section class="section reveal" :style="{ transitionDelay: '90ms' }">
          <h3 class="section-label">PARAMETERS / 参数估计</h3>
          <div class="section-rule"></div>
          <p v-if="!statsStore.estimates?.length" class="export-hint">运行估算后将显示路径/载荷等参数（含标准化估计 β）。</p>
          <div v-else class="est-table-wrap">
            <table class="est-table">
              <thead>
                <tr>
                  <th>lval</th>
                  <th>op</th>
                  <th>rval</th>
                  <th>Estimate</th>
                  <th>β (Std)</th>
                  <th>S.E.</th>
                  <th>C.R.</th>
                  <th>p</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(r, idx) in statsStore.estimates" :key="`est-${idx}`">
                  <td>{{ r.lval }}</td>
                  <td>{{ r.op }}</td>
                  <td>{{ r.rval }}</td>
                  <td>{{ fmt(r.estimate) }}</td>
                  <td>{{ fmt(r.est_std) }}</td>
                  <td>{{ fmt(r.std_err) }}</td>
                  <td>{{ fmt(r.z_value) }}</td>
                  <td>{{ fmtP(r.p_value) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="section reveal" :style="{ transitionDelay: '96ms' }">
          <h3 class="section-label">PATH SUMMARY / 路径显著性汇总</h3>
          <div class="section-rule"></div>
          <p v-if="!statsStore.estimates?.length" class="export-hint">运行估算后，这里会自动汇总结构回归路径（op='~'）的显著性，并生成可复制的论文式结果段落。</p>
          <div v-else>
            <p v-if="!pathSummaryRows.length" class="export-hint">未在参数表中识别到可汇总的结构回归路径（op='~' 且含 p 值）。</p>
            <div v-else class="est-table-wrap">
              <table class="est-table">
                <thead>
                  <tr>
                    <th>predictor</th>
                    <th>outcome</th>
                    <th>β (Std)</th>
                    <th>p</th>
                    <th>sig</th>
                    <th>direction</th>
                    <th>note</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(r, idx) in pathSummaryRows" :key="`path-sum-${idx}`">
                    <td>{{ r.predictor }}</td>
                    <td>{{ r.outcome }}</td>
                    <td>{{ fmt(r.beta) }}</td>
                    <td>{{ fmtP(r.p_value) }}</td>
                    <td>{{ r.significant ? 'YES' : 'NO' }}</td>
                    <td>{{ r.direction }}</td>
                    <td>{{ r.note || '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div v-if="pathSummaryReportText" class="inv-report" style="margin-top: 0.85rem;">
              <div class="inv-report-top">
                <div class="inv-report-title">可复制结果段落（UI 自动生成）</div>
                <button type="button" :class="[BTN.ghost, 'inv-report-copy']" @click="copyText(pathSummaryReportText, '已复制路径摘要段落')">
                  复制段落
                </button>
              </div>
              <pre class="inv-report-pre">{{ pathSummaryReportText }}</pre>
            </div>

            <div v-if="bootstrapFxBridgeLines.length" class="export-hint" style="margin-top: 0.75rem">
              <strong>与 Bootstrap 分解联动（直接/总效应）：</strong>
              <ul style="margin: 0.35rem 0 0 1rem; padding: 0">
                <li v-for="(line, i) in bootstrapFxBridgeLines" :key="`fx-br-${i}`">{{ line }}</li>
              </ul>
            </div>

            <div class="inv-report" style="margin-top: 1rem">
              <div class="inv-report-top">
                <div class="inv-report-title">综合结果摘要（拟合 + 路径 + 可选 Bootstrap / 调节）</div>
                <button
                  type="button"
                  :class="[BTN.ghost, 'inv-report-copy']"
                  :disabled="!integratedPaperParagraph"
                  @click="copyText(integratedPaperParagraph, '已复制综合结果摘要段落')"
                >
                  复制整合段落
                </button>
              </div>
              <p v-if="!integratedPaperParagraph" class="export-hint">
                完成 ML 估算、或具备路径汇总 / Bootstrap 中介 / 有调节的中介 / 观测变量调节 等任一项结果后，将在此生成可粘贴论文的整合段落（仍须按期刊要求人工校对）。
              </p>
              <pre v-else class="inv-report-pre">{{ integratedPaperParagraph }}</pre>
            </div>
          </div>
        </section>

        <section class="section reveal" :style="{ transitionDelay: '98ms' }">
          <h3 class="section-label">LATENT INTERACTION / 潜变量交互</h3>
          <div class="section-rule"></div>
          <p class="export-hint">
            在已写好的 lavaan 语法上拟合并筛选与 F1、F2 相关的结构路径（semopy）。请先在建模页追加交互骨架或手写交互项。
          </p>
          <div class="config-row">
            <div class="config-item">
              <label class="config-label osem-field-label">结局 Y</label>
              <input v-model.trim="liProbeY" :class="[INP.input, 'project-name-input']" type="text" placeholder="如 Y 或潜变量名" :disabled="statsStore.latentInteractionRunning" />
            </div>
            <div class="config-item">
              <label class="config-label osem-field-label">F1</label>
              <input v-model.trim="liProbeF1" :class="[INP.input, 'project-name-input']" type="text" placeholder="潜变量 1" :disabled="statsStore.latentInteractionRunning" />
            </div>
            <div class="config-item">
              <label class="config-label osem-field-label">F2</label>
              <input v-model.trim="liProbeF2" :class="[INP.input, 'project-name-input']" type="text" placeholder="潜变量 2" :disabled="statsStore.latentInteractionRunning" />
            </div>
            <div class="config-item" style="align-self: flex-end">
              <button
                :class="BTN.primary"
                :disabled="statsStore.latentInteractionRunning || !canRunLatentInteractionProbe"
                @click="runLatentInteractionProbe"
              >
                {{ statsStore.latentInteractionRunning ? `运行中…${statsStore.latentInteractionTaskProgress || 0}%` : '运行 潜变量交互探测' }}
              </button>
            </div>
          </div>
          <p v-if="statsStore.latentInteractionError" class="fit-error">{{ statsStore.latentInteractionError }}</p>
          <p v-if="statsStore.latentInteractionErrorHint" class="fit-error-hint">{{ statsStore.latentInteractionErrorHint }}</p>
          <div v-if="statsStore.latentInteractionResult?.boundary" class="used-n" style="margin-bottom: 0.5rem">
            {{ statsStore.latentInteractionResult.boundary.semopy }}
          </div>
          <div v-if="statsStore.latentInteractionResult?.matching?.length" class="est-table-wrap">
            <div class="used-n">候选交互路径（matching）</div>
            <table class="est-table">
              <thead>
                <tr>
                  <th>lval</th>
                  <th>op</th>
                  <th>rval</th>
                  <th>β</th>
                  <th>p</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(r, idx) in statsStore.latentInteractionResult.matching" :key="`li-m-${idx}`">
                  <td>{{ r.lval }}</td>
                  <td>{{ r.op }}</td>
                  <td>{{ r.rval }}</td>
                  <td>{{ fmt(r.est_std ?? r.estimate) }}</td>
                  <td>{{ fmtP(r.p_value) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else-if="statsStore.latentInteractionResult && !statsStore.latentInteractionRunning" class="export-hint">
            未匹配到含 F1、F2 的交互写法（可检查语法右侧是否含 F1:F2、乘积潜变量等）。
          </p>
        </section>

        <section class="section reveal" :style="{ transitionDelay: '105ms' }">
          <h3 class="section-label">DIAGRAM / 路径图</h3>
          <div class="section-rule"></div>
          <SemGraph :lavaan-syntax="modelStore.lavaanSyntax" :estimates="statsStore.estimates || []" />
        </section>

        <section class="section reveal" :style="{ transitionDelay: '112ms' }">
          <h3 class="section-label">BOOTSTRAP / 中介效应</h3>
          <div class="section-rule"></div>
          <p class="export-hint">
            支持 sequence / sequence_text 与 label；服务端会校验标识符与 lavaan 语法/数据列一致。同一 `X → Y` 下多条路径会汇总总间接，并输出直接效应与总效应行。
          </p>

          <div class="config-row">
            <div class="config-item">
              <label class="config-label osem-field-label">X</label>
              <select v-model="medDraftX" :class="INP.select" :disabled="statsStore.bootstrapping">
                <option value="">请选择</option>
                <option v-for="v in variableNames" :key="`x-${v}`" :value="v">{{ v }}</option>
              </select>
            </div>
            <div class="config-item">
              <label class="config-label osem-field-label">中介链</label>
              <input
                v-model.trim="medDraftChain"
                :class="[INP.input, 'project-name-input']"
                type="text"
                placeholder="例如：M1 或 M1, M2"
                :disabled="statsStore.bootstrapping"
              />
            </div>
            <div class="config-item">
              <label class="config-label osem-field-label">Y</label>
              <select v-model="medDraftY" :class="INP.select" :disabled="statsStore.bootstrapping">
                <option value="">请选择</option>
                <option v-for="v in variableNames" :key="`y-${v}`" :value="v">{{ v }}</option>
              </select>
            </div>
            <div class="config-item">
              <label class="config-label osem-field-label">次数</label>
              <select v-model.number="bootN" :class="INP.select" :disabled="statsStore.bootstrapping">
                <option :value="200">200（快速）</option>
                <option :value="1000">1000（推荐）</option>
                <option :value="2000">2000（默认）</option>
                <option :value="5000">5000（更稳）</option>
              </select>
            </div>
            <div class="config-item" style="min-width: 18rem;">
              <label class="config-label osem-field-label">协变量（可选）</label>
              <input
                v-model.trim="bootCovariatesText"
                :class="[INP.input, 'project-name-input']"
                type="text"
                placeholder="例如：C1, C2（将作为主效应控制）"
                :disabled="statsStore.bootstrapping"
              />
            </div>
          </div>

          <div class="action-row" style="margin-top: -0.15rem;">
            <button :class="BTN.ghost" :disabled="statsStore.bootstrapping || !canAddMediationEffect" @click="addMediationEffect">
              添加效应路径
            </button>
            <button :class="BTN.ghost" :disabled="statsStore.bootstrapping || !mediationEffects.length" @click="clearMediationEffects">
              清空已添加路径
            </button>
            <span class="used-n">已添加 {{ mediationEffects.length }} 条路径</span>
          </div>

          <div v-if="mediationEffects.length" class="mi-list" style="margin-bottom: 0.9rem;">
            <div v-for="(effect, idx) in mediationEffects" :key="effect.id" class="mi-item">
              <div class="mi-formula">{{ effect.label }}</div>
              <div class="mi-meta">类型：{{ effect.sequence.length > 3 ? '链式中介' : '单/并联中介路径' }}</div>
              <div class="mi-item-actions">
                <button type="button" class="mi-apply-btn mi-ignore-btn" @click="removeMediationEffect(idx)">移除</button>
              </div>
            </div>
          </div>

          <div class="action-row">
            <button :class="BTN.primary" :disabled="statsStore.bootstrapping || !canFit || !canRunBootstrap" @click="runBootstrap">
              {{ statsStore.bootstrapping ? `运行中…${statsStore.bootstrapTaskProgress || 0}%` : '运行 Bootstrap' }}
            </button>
          </div>
          <div
            v-if="bootstrapFeedback"
            :class="[FEEDBACK.base, resolveFeedbackTone(bootstrapFeedback.kind), 'bootstrap-feedback']"
          >
            <p :class="FEEDBACK.text">{{ bootstrapFeedback.text }}</p>
            <p :class="FEEDBACK.detail">{{ bootstrapFeedback.detail }}</p>
          </div>

          <div v-if="statsStore.bootstrapResult?.items?.length" class="est-table-wrap">
            <p v-if="statsStore.bootstrapResult?.covariates?.length" class="used-n" style="margin: 0 0 0.45rem 0;">
              协变量（主效应）：{{ (statsStore.bootstrapResult.covariates || []).join(', ') }}
            </p>
            <table class="est-table">
              <thead>
                <tr>
                  <th>类型</th>
                  <th>标签</th>
                  <th>路径</th>
                  <th>效应值（点估计）</th>
                  <th>CI（percentile）</th>
                  <th>CI（BC）</th>
                  <th>有效样本（boot）</th>
                  <th>说明</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(r, idx) in statsStore.bootstrapResult.items" :key="`boot-${idx}`">
                  <td>{{ bootstrapEffectTypeLabel(r.effect_type) }}</td>
                  <td>{{ r.label || '—' }}</td>
                  <td>{{ r.path_label || fmtSequence(r.sequence) }}</td>
                  <td>{{ fmt(r.indirect_point) }}</td>
                  <td>{{ fmtCi(r.ci?.percentile) }}</td>
                  <td>{{ fmtCi(r.ci?.bc) }}</td>
                  <td>{{ r.ci?.n_boot_valid ?? '—' }}</td>
                  <td>{{ r.note || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="section reveal" :style="{ transitionDelay: '116ms' }">
          <h3 class="section-label">MODERATION / 调节效应</h3>
          <div class="section-rule"></div>
          <p class="export-hint">当前先提供观测变量调节的最小闭环：支持连续型 `W` 与分类 `W`，返回交互项与简单斜率摘要。</p>

          <div class="config-row">
            <div class="config-item">
              <label class="config-label osem-field-label">X</label>
              <select v-model="modX" :class="INP.select" :disabled="statsStore.moderationRunning">
                <option value="">请选择</option>
                <option v-for="v in variableNames" :key="`mod-x-${v}`" :value="v">{{ v }}</option>
              </select>
            </div>
            <div class="config-item">
              <label class="config-label osem-field-label">W（调节变量）</label>
              <select v-model="modW" :class="INP.select" :disabled="statsStore.moderationRunning">
                <option value="">请选择</option>
                <option v-for="v in variableNames" :key="`mod-w-${v}`" :value="v">{{ v }}</option>
              </select>
            </div>
            <div class="config-item">
              <label class="config-label osem-field-label">Y</label>
              <select v-model="modY" :class="INP.select" :disabled="statsStore.moderationRunning">
                <option value="">请选择</option>
                <option v-for="v in variableNames" :key="`mod-y-${v}`" :value="v">{{ v }}</option>
              </select>
            </div>
            <div class="config-item">
              <label class="config-label osem-field-label">W 类型</label>
              <select v-model="modType" :class="INP.select" :disabled="statsStore.moderationRunning">
                <option value="continuous">连续变量</option>
                <option value="categorical">分类变量</option>
              </select>
            </div>
            <div class="config-item" style="min-width: 18rem;">
              <label class="config-label osem-field-label">协变量（可选）</label>
              <input
                v-model.trim="modCovariatesText"
                :class="[INP.input, 'project-name-input']"
                type="text"
                placeholder="例如：C1, C2（将作为控制变量加入回归）"
                :disabled="statsStore.moderationRunning"
              />
            </div>
          </div>

          <div class="action-row">
            <button :class="BTN.primary" :disabled="statsStore.moderationRunning || !canRunModeration" @click="runModeration">
              {{ statsStore.moderationRunning ? `运行中…${statsStore.moderationTaskProgress || 0}%` : '运行 调节分析' }}
            </button>
            <span v-if="statsStore.moderationRunning && statsStore.moderationTaskMessage" class="used-n">
              {{ statsStore.moderationTaskMessage }}
            </span>
          </div>
          <p v-if="statsStore.moderationError" class="fit-error">{{ statsStore.moderationError }}</p>
          <p v-if="statsStore.moderationErrorHint" class="fit-error-hint">{{ statsStore.moderationErrorHint }}</p>

          <div v-if="statsStore.moderationResult?.coefficients?.length" class="est-table-wrap">
            <table class="est-table">
              <thead>
                <tr>
                  <th>term</th>
                  <th>Estimate</th>
                  <th>S.E.</th>
                  <th>z</th>
                  <th>p</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in statsStore.moderationResult.coefficients" :key="`mod-coef-${idx}`">
                  <td>{{ row.term }}</td>
                  <td>{{ fmt(row.estimate) }}</td>
                  <td>{{ fmt(row.std_err) }}</td>
                  <td>{{ fmt(row.z_value) }}</td>
                  <td>{{ fmtP(row.p_value) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="statsStore.moderationResult?.simple_slopes?.length" class="est-table-wrap" style="margin-top: 0.75rem;">
            <table class="est-table">
              <thead>
                <tr>
                  <th>组别 / 水平</th>
                  <th>X→Y 简单斜率</th>
                  <th>W 值</th>
                  <th>说明</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in statsStore.moderationResult.simple_slopes" :key="`mod-slope-${idx}`">
                  <td>{{ row.group }}</td>
                  <td>{{ fmt(row.slope_x) }}</td>
                  <td>{{ fmt(row.w_value) }}</td>
                  <td>{{ row.note || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="section reveal" :style="{ transitionDelay: '118ms' }">
          <h3 class="section-label">MODERATED MEDIATION / 有调节的中介</h3>
          <div class="section-rule"></div>
          <p class="export-hint">
            <strong>Model 7</strong>：W 调节 X→M，Y ~ M + X + W + 协变量。W 为连续时在均值与 ±1SD 报告条件间接；W 为分类时用虚拟编码并给出各类别条件间接，指数对比<strong>排序末类 vs 参考组（首类）</strong>。
            <strong>Model 14</strong>：W 调节 M→Y（第一阶段 M ~ X），仅<strong>连续</strong> W；条件间接为 a·(b<sub>M</sub>+b<sub>MW</sub>·W)。
          </p>

          <div class="config-row">
            <div class="config-item">
              <label class="config-label osem-field-label">PROCESS</label>
              <select v-model="mmHayesModel" :class="INP.select" :disabled="statsStore.moderatedMediationRunning">
                <option value="7">Model 7（W 调节 X→M）</option>
                <option value="14">Model 14（W 调节 M→Y）</option>
              </select>
            </div>
            <div class="config-item">
              <label class="config-label osem-field-label">W 类型</label>
              <select v-model="mmWType" :class="INP.select" :disabled="statsStore.moderatedMediationRunning || mmHayesModel === '14'">
                <option value="continuous">连续</option>
                <option value="categorical">分类（虚拟编码）</option>
              </select>
            </div>
            <div class="config-item">
              <label class="config-label osem-field-label">X</label>
              <select v-model="mmX" :class="INP.select" :disabled="statsStore.moderatedMediationRunning">
                <option value="">请选择</option>
                <option v-for="v in variableNames" :key="`mm-x-${v}`" :value="v">{{ v }}</option>
              </select>
            </div>
            <div class="config-item">
              <label class="config-label osem-field-label">M（中介）</label>
              <select v-model="mmM" :class="INP.select" :disabled="statsStore.moderatedMediationRunning">
                <option value="">请选择</option>
                <option v-for="v in variableNames" :key="`mm-m-${v}`" :value="v">{{ v }}</option>
              </select>
            </div>
            <div class="config-item">
              <label class="config-label osem-field-label">Y</label>
              <select v-model="mmY" :class="INP.select" :disabled="statsStore.moderatedMediationRunning">
                <option value="">请选择</option>
                <option v-for="v in variableNames" :key="`mm-y-${v}`" :value="v">{{ v }}</option>
              </select>
            </div>
            <div class="config-item">
              <label class="config-label osem-field-label">W（调节变量）</label>
              <select v-model="mmW" :class="INP.select" :disabled="statsStore.moderatedMediationRunning">
                <option value="">请选择</option>
                <option v-for="v in variableNames" :key="`mm-w-${v}`" :value="v">{{ v }}</option>
              </select>
            </div>
            <div class="config-item">
              <label class="config-label osem-field-label">Bootstrap 次数</label>
              <select v-model.number="mmBootN" :class="INP.select" :disabled="statsStore.moderatedMediationRunning">
                <option :value="200">200（快速）</option>
                <option :value="1000">1000</option>
                <option :value="2000">2000（默认）</option>
                <option :value="5000">5000</option>
              </select>
            </div>
            <div class="config-item" style="min-width: 18rem;">
              <label class="config-label osem-field-label">协变量（可选）</label>
              <input
                v-model.trim="mmCovariatesText"
                :class="[INP.input, 'project-name-input']"
                type="text"
                placeholder="例如：C1, C2（两方程均加入主效应）"
                :disabled="statsStore.moderatedMediationRunning"
              />
            </div>
          </div>

          <div class="action-row">
            <button
              :class="BTN.primary"
              :disabled="statsStore.moderatedMediationRunning || !canRunModeratedMediation"
              @click="runModeratedMediation"
            >
              {{ statsStore.moderatedMediationRunning ? `运行中…${statsStore.moderatedMediationTaskProgress || 0}%` : '运行 有调节的中介' }}
            </button>
            <span v-if="statsStore.moderatedMediationRunning && statsStore.moderatedMediationTaskMessage" class="used-n">
              {{ statsStore.moderatedMediationTaskMessage }}
            </span>
          </div>
          <p v-if="statsStore.moderatedMediationError" class="fit-error">{{ statsStore.moderatedMediationError }}</p>
          <p v-if="statsStore.moderatedMediationErrorHint" class="fit-error-hint">{{ statsStore.moderatedMediationErrorHint }}</p>

          <div v-if="statsStore.moderatedMediationResult?.conditional_indirect?.length" class="est-table-wrap">
            <p class="used-n" style="margin: 0 0 0.45rem 0;">
              模型：{{ statsStore.moderatedMediationResult.model || 'hayes_process_7' }} · N={{ statsStore.moderatedMediationResult.n_used }} · Boot={{ statsStore.moderatedMediationResult.n_boot }}
            </p>
            <table class="est-table">
              <thead>
                <tr>
                  <th>W 水平</th>
                  <th>W 值</th>
                  <th>条件间接效应</th>
                  <th>CI（percentile）</th>
                  <th>CI（BC）</th>
                  <th>有效 boot</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in statsStore.moderatedMediationResult.conditional_indirect" :key="`mm-ci-${idx}`">
                  <td>{{ row.label }}</td>
                  <td>{{ fmt(row.w_value) }}</td>
                  <td>{{ fmt(row.indirect_point) }}</td>
                  <td>{{ fmtCi(row.ci?.percentile) }}</td>
                  <td>{{ fmtCi(row.ci?.bc) }}</td>
                  <td>{{ row.ci?.n_boot_valid ?? '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div
            v-if="statsStore.moderatedMediationResult?.index_moderated_mediation"
            class="est-table-wrap"
            style="margin-top: 0.75rem;"
          >
            <table class="est-table">
              <thead>
                <tr>
                  <th>指数（条件间接之差）</th>
                  <th>点估计</th>
                  <th>CI（percentile）</th>
                  <th>CI（BC）</th>
                  <th>有效 boot</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>{{ statsStore.moderatedMediationResult.index_moderated_mediation.contrast }}</td>
                  <td>{{ fmt(statsStore.moderatedMediationResult.index_moderated_mediation.point) }}</td>
                  <td>{{ fmtCi(statsStore.moderatedMediationResult.index_moderated_mediation.ci?.percentile) }}</td>
                  <td>{{ fmtCi(statsStore.moderatedMediationResult.index_moderated_mediation.ci?.bc) }}</td>
                  <td>{{ statsStore.moderatedMediationResult.index_moderated_mediation.ci?.n_boot_valid ?? '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="section reveal" :style="{ transitionDelay: '116ms' }">
          <h3 class="section-label">MODEL COMPARE / 模型比较</h3>
          <div class="section-rule"></div>
          <p class="export-hint">
            用于比较两个模型（AIC/BIC + 嵌套模型 LRT）。默认以“当前语法”为 Model A；请在下方粘贴 Model B（通常为更简化/加约束的嵌套模型）。
            若当前环境未启用 lavaan，将自动降级：仍展示 AIC/BIC（若可用）但 LRT 置空并提示原因。
          </p>

          <div class="config-row">
            <div class="config-item">
              <label class="config-label osem-field-label">Model A 标签</label>
              <input v-model="compareLabelA" :class="INP.input" style="height: 38px;" :disabled="statsStore.modelCompareRunning" />
            </div>
            <div class="config-item">
              <label class="config-label osem-field-label">Model B 标签</label>
              <input v-model="compareLabelB" :class="INP.input" style="height: 38px;" :disabled="statsStore.modelCompareRunning" />
            </div>
          </div>

          <div class="config-row" style="margin-top: 0.35rem;">
            <div class="config-item" style="grid-column: 1 / -1;">
              <label class="config-label osem-field-label">Model B lavaan 语法</label>
              <textarea
                v-model="compareSyntaxB"
                :class="INP.textarea"
                rows="8"
                :disabled="statsStore.modelCompareRunning"
                placeholder="请粘贴需要比较的 Model B lavaan 语法（建议为嵌套模型：删路径/加约束）。"
              ></textarea>
              <div class="action-row" style="margin-top: 0.45rem;">
                <button :class="BTN.ghost" :disabled="statsStore.modelCompareRunning || !canExportSyntax" @click="copyCurrentSyntaxToB">
                  复制当前语法到 Model B
                </button>
                <span class="used-n">Model A 使用当前语法版本：{{ currentSyntaxTag }}</span>
              </div>
            </div>
          </div>

          <div class="action-row">
            <button :class="BTN.primary" :disabled="statsStore.modelCompareRunning || !canRunModelCompare" @click="runModelCompare">
              {{ statsStore.modelCompareRunning ? `比较中…${statsStore.modelCompareTaskProgress || 0}%` : '运行 模型比较' }}
            </button>
          </div>
          <div
            v-if="modelCompareFeedback"
            :class="[FEEDBACK.base, resolveFeedbackTone(modelCompareFeedback.kind), 'model-compare-feedback']"
          >
            <p :class="FEEDBACK.text">{{ modelCompareFeedback.text }}</p>
            <p :class="FEEDBACK.detail">{{ modelCompareFeedback.detail }}</p>
          </div>

          <div v-if="statsStore.modelCompareResult?.models?.length" class="est-table-wrap">
            <table class="est-table">
              <thead>
                <tr>
                  <th>模型</th>
                  <th>AIC</th>
                  <th>BIC</th>
                  <th>χ²</th>
                  <th>df</th>
                  <th>CFI</th>
                  <th>TLI</th>
                  <th>RMSEA</th>
                  <th>SRMR</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(m, idx) in statsStore.modelCompareResult.models" :key="`mc-m-${idx}`">
                  <td>{{ m.label || '—' }}</td>
                  <td>{{ fmt(m.fit?.aic) }}</td>
                  <td>{{ fmt(m.fit?.bic) }}</td>
                  <td>{{ fmt(m.fit?.chi2) }}</td>
                  <td>{{ fmt(m.fit?.df) }}</td>
                  <td>{{ fmt(m.fit?.cfi) }}</td>
                  <td>{{ fmt(m.fit?.tli) }}</td>
                  <td>{{ fmt(m.fit?.rmsea) }}</td>
                  <td>{{ fmt(m.fit?.srmr) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="statsStore.modelCompareResult?.comparison" class="est-table-wrap" style="margin-top: 0.75rem;">
            <table class="est-table">
              <thead>
                <tr>
                  <th>From</th>
                  <th>To</th>
                  <th>Δχ²</th>
                  <th>Δdf</th>
                  <th>p</th>
                  <th>说明</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>{{ statsStore.modelCompareResult.comparison.from || '—' }}</td>
                  <td>{{ statsStore.modelCompareResult.comparison.to || '—' }}</td>
                  <td>{{ fmt(statsStore.modelCompareResult.comparison.chi2_diff) }}</td>
                  <td>{{ fmt(statsStore.modelCompareResult.comparison.df_diff) }}</td>
                  <td>{{ fmtP(statsStore.modelCompareResult.comparison.p_value) }}</td>
                  <td>{{ statsStore.modelCompareResult.comparison.note || (statsStore.modelCompareResult.comparison.ok ? '—' : '不可比/不可用') }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section
          class="section reveal"
          :class="DENSE.zone"
          :style="{ transitionDelay: '116ms' }"
        >
          <h3 class="section-label">INVARIANCE / 多群组（配置不变性）</h3>
          <div class="section-rule"></div>
          <p class="export-hint">当前仅支持“配置不变性”：按分组变量拆分后分别拟合各组并汇总拟合度与参数表（不施加等值约束）。</p>

          <div class="config-row">
            <div class="config-item">
              <label class="config-label osem-field-label">分组变量</label>
              <select v-model="groupVar" :class="INP.select" :disabled="statsStore.invarianceRunning">
                <option value="">请选择</option>
                <option v-for="v in variableNames" :key="`g-${v}`" :value="v">{{ v }}</option>
              </select>
            </div>
          </div>

          <div class="action-row">
            <button :class="BTN.primary" :disabled="statsStore.invarianceRunning || !canFit || !groupVar" @click="runInvariance">
              {{ statsStore.invarianceRunning ? `运行中…${statsStore.invarianceTaskProgress || 0}%` : '运行 多群组(配置)' }}
            </button>
            <span v-if="statsStore.invarianceRunning && statsStore.invarianceTaskMessage" class="used-n">{{ statsStore.invarianceTaskMessage }}</span>
          </div>
          <p v-if="statsStore.invarianceError" class="fit-error">{{ statsStore.invarianceError }}</p>
          <p v-if="statsStore.invarianceErrorHint" class="fit-error-hint">{{ statsStore.invarianceErrorHint }}</p>

          <div class="action-row" style="margin-top: 0.25rem;">
            <button
              :class="BTN.ghost"
              :disabled="statsStore.invarianceSeriesRunning || !canFit || !groupVar || !lavaanAvailable"
              @click="runInvarianceSeries"
            >
              {{
                statsStore.invarianceSeriesRunning
                  ? `序列检验中…${statsStore.invarianceSeriesTaskProgress || 0}%`
                  : invSeriesGate.degraded
                    ? '不变性序列已降级（查看原因/重试）'
                    : '运行 不变性序列(lavaan)'
              }}
            </button>
            <span v-if="statsStore.invarianceSeriesRunning && statsStore.invarianceSeriesTaskMessage" class="used-n">{{ statsStore.invarianceSeriesTaskMessage }}</span>
          </div>
          <div
            v-if="invarianceSeriesFeedback"
            :class="[FEEDBACK.base, resolveFeedbackTone(invarianceSeriesFeedback.kind), 'invariance-series-feedback']"
          >
            <p :class="FEEDBACK.text">{{ invarianceSeriesFeedback.text }}</p>
            <p :class="FEEDBACK.detail">{{ invarianceSeriesFeedback.detail }}</p>
          </div>
          <p
            v-if="invSeriesGate.degraded || !lavaanAvailable"
            class="export-hint"
          >
            {{ !lavaanAvailable ? (lavaanGateText || invSeriesGate.message) : invSeriesGate.message }}
          </p>

          <div v-if="statsStore.invarianceResult?.items?.length" class="est-table-wrap">
            <table class="est-table">
              <thead>
                <tr>
                  <th>组别</th>
                  <th>N</th>
                  <th>status</th>
                  <th>χ²/df</th>
                  <th>RMSEA</th>
                  <th>CFI</th>
                  <th>TLI</th>
                  <th>SRMR</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(g, idx) in statsStore.invarianceResult.items" :key="`inv-${idx}`">
                  <td>{{ g.group }}</td>
                  <td>{{ g.n_used ?? '—' }}</td>
                  <td>{{ g.fit_indices?.status ?? (g.success ? '—' : 'fail') }}</td>
                  <td>{{ g.fit_indices?.chi2_df ?? '—' }}</td>
                  <td>{{ g.fit_indices?.rmsea ?? '—' }}</td>
                  <td>{{ g.fit_indices?.cfi ?? '—' }}</td>
                  <td>{{ g.fit_indices?.tli ?? '—' }}</td>
                  <td>{{ g.fit_indices?.srmr ?? '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="statsStore.invarianceSeriesResult?.models?.length" class="est-table-wrap" style="margin-top: 0.75rem;">
            <table class="est-table">
              <thead>
                <tr>
                  <th>模型</th>
                  <th>等值约束</th>
                  <th>χ²</th>
                  <th>df</th>
                  <th>CFI</th>
                  <th>TLI</th>
                  <th>RMSEA</th>
                  <th>SRMR</th>
                  <th>converged</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(m, idx) in statsStore.invarianceSeriesResult.models" :key="`inv-series-${idx}`">
                  <td>{{ m.model }}</td>
                  <td>{{ Array.isArray(m.group_equal) ? m.group_equal.join(', ') : m.group_equal || '—' }}</td>
                  <td>{{ fmt(m.fit?.chi2) }}</td>
                  <td>{{ fmt(m.fit?.df) }}</td>
                  <td>{{ fmt(m.fit?.cfi) }}</td>
                  <td>{{ fmt(m.fit?.tli) }}</td>
                  <td>{{ fmt(m.fit?.rmsea) }}</td>
                  <td>{{ fmt(m.fit?.srmr) }}</td>
                  <td>{{ m.converged ?? '—' }}</td>
                </tr>
              </tbody>
            </table>
            <p v-if="statsStore.invarianceSeriesResult?.note" class="export-hint">{{ statsStore.invarianceSeriesResult.note }}</p>
          </div>

          <div v-if="invModelCards.length" class="inv-cards inv-model-cards">
            <div v-for="(card, idx) in invModelCards" :key="`inv-model-card-${idx}`" class="inv-card">
              <div class="inv-card-top">
                <div class="inv-card-title">{{ card.title }}</div>
                <div class="inv-card-badge" :class="`inv-badge-${card.status}`">{{ card.badge }}</div>
              </div>
              <div class="inv-card-body">
                <div class="inv-card-row">
                  <span class="inv-card-k">收敛</span>
                  <span class="inv-card-v">{{ card.convergedText }}</span>
                </div>
                <div class="inv-card-row">
                  <span class="inv-card-k">CFI / TLI</span>
                  <span class="inv-card-v">{{ card.cfiTli }}</span>
                </div>
                <div class="inv-card-row">
                  <span class="inv-card-k">RMSEA / SRMR</span>
                  <span class="inv-card-v">{{ card.rmseaSrmr }}</span>
                </div>
                <div class="inv-card-row">
                  <span class="inv-card-k">χ² / df</span>
                  <span class="inv-card-v">{{ card.chi2Df }}</span>
                </div>
              </div>
            </div>
          </div>

          <div v-if="statsStore.invarianceSeriesResult?.comparisons?.length" class="est-table-wrap" style="margin-top: 0.75rem;">
            <table class="est-table">
              <thead>
                <tr>
                  <th>对比</th>
                  <th>ok</th>
                  <th>Δχ²</th>
                  <th>Δdf</th>
                  <th>p</th>
                  <th>ΔCFI</th>
                  <th>ΔRMSEA</th>
                  <th>note</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(c, idx) in statsStore.invarianceSeriesResult.comparisons" :key="`inv-comp-${idx}`">
                  <td>{{ c.from && c.to ? `${c.from} → ${c.to}` : '—' }}</td>
                  <td>{{ invStepBadge(c).badge }}</td>
                  <td>{{ fmt(c.chi2_diff) }}</td>
                  <td>{{ fmt(c.df_diff) }}</td>
                  <td>{{ fmtP(c.p_value) }}</td>
                  <td>{{ fmt(c.delta_cfi) }}</td>
                  <td>{{ fmt(c.delta_rmsea) }}</td>
                  <td>{{ invStepBadge(c).note }}</td>
                </tr>
              </tbody>
            </table>
            <p v-if="invSeriesSummaryLines.length" class="export-hint" style="margin-top: 0.5rem;">
              <span v-for="(line, i) in invSeriesSummaryLines" :key="`inv-sum-${i}`" style="display: block;">
                {{ line }}
              </span>
            </p>
          </div>

          <div v-if="invSeriesCards.length" class="inv-cards">
            <div v-for="(card, idx) in invSeriesCards" :key="`inv-card-${idx}`" class="inv-card">
              <div class="inv-card-top">
                <div class="inv-card-title">{{ card.title }}</div>
                <div class="inv-card-badge" :class="`inv-badge-${card.status}`">{{ card.badge }}</div>
              </div>
              <div class="inv-card-body">
                <div class="inv-card-row">
                  <span class="inv-card-k">经验阈值</span>
                  <span class="inv-card-v">{{ card.threshold }}</span>
                </div>
                <div class="inv-card-row">
                  <span class="inv-card-k">关键证据</span>
                  <span class="inv-card-v">{{ card.evidence }}</span>
                </div>
                <div class="inv-card-row">
                  <span class="inv-card-k">原因</span>
                  <span class="inv-card-v">{{ card.reason }}</span>
                </div>
              </div>
            </div>
          </div>

          <div v-if="invSeriesReportTextLite || invSeriesReportTextStrict" class="inv-report">
            <p class="export-hint" style="margin-bottom: 0.6rem;">
              说明：lite 常用于“至少到 scalar”的发表场景；strict 在此基础上再增加残差等值（更严格，失败更常见）。建议优先使用上方逐步 PASS/FAIL
              作为结论依据，并结合理论合理性。
            </p>

            <div v-if="invSeriesReportTextLite" class="inv-report" style="margin-top: 0;">
              <div class="inv-report-top">
                <div class="inv-report-title">可复制报告段落（lite：到 scalar）</div>
                <button type="button" :class="[BTN.ghost, 'inv-report-copy']" @click="copyText(invSeriesReportTextLite, '已复制不变性报告段落（lite）')">
                  复制
                </button>
              </div>
              <pre class="inv-report-pre">{{ invSeriesReportTextLite }}</pre>
            </div>

            <div v-if="invSeriesReportTextStrict" class="inv-report" style="margin-top: 0.8rem;">
              <div class="inv-report-top">
                <div class="inv-report-title">可复制报告段落（strict：到 strict）</div>
                <button
                  type="button"
                  :class="[BTN.ghost, 'inv-report-copy']"
                  @click="copyText(invSeriesReportTextStrict, '已复制不变性报告段落（strict）')"
                >
                  复制
                </button>
              </div>
              <pre class="inv-report-pre">{{ invSeriesReportTextStrict }}</pre>
            </div>
          </div>
        </section>

        <section class="section reveal" :style="{ transitionDelay: '118ms' }">
          <h3 class="section-label">MGA / 结构路径跨组逐步比较</h3>
          <div class="section-rule"></div>
          <p class="export-hint">
            在已选择“分组变量”的前提下，基于当前参数表（estimates）自动识别结构回归路径（op='~'），并支持按
            测量不变性层级（configural/metric/scalar/strict）×结构路径，逐条执行“仅该路径等值约束”的嵌套模型 LRT。
            若未启用 lavaan，将降级为各组分别拟合的系数对照（无 LRT）。
          </p>

          <div class="config-row">
            <div class="config-item">
              <label class="config-label osem-field-label">分组变量</label>
              <select v-model="groupVar" :class="INP.select" :disabled="statsStore.mgaRunning">
                <option value="">请选择</option>
                <option v-for="v in variableNames" :key="`mga-g-${v}`" :value="v">{{ v }}</option>
              </select>
            </div>
          </div>

          <div v-if="!mgaPathOptions.length" class="export-hint" style="margin-top: 0.35rem;">
            提示：请先运行一次“估算”，系统会从参数表中自动识别结构回归路径（op='~'）供勾选。
          </div>
          <div v-else class="mi-adoptions" style="margin-top: 0.35rem;">
            <div class="mi-toolbar" style="margin-top: 0;">
              <span class="mi-count">已选 {{ mgaSelectedKeys.length }} / {{ mgaPathOptions.length }} 条结构回归路径</span>
              <button type="button" class="mi-apply-link" :disabled="statsStore.mgaRunning" @click="selectAllMgaPaths">
                全选
              </button>
              <button type="button" class="mi-apply-link" :disabled="statsStore.mgaRunning" @click="clearMgaPaths">
                全不选
              </button>
            </div>
            <div v-for="opt in mgaPathOptions" :key="`mga-opt-${opt.key}`" class="mi-adopt-item" style="padding: 0.55rem 0.75rem;">
              <label class="export-stale-toggle" style="margin: 0;">
                <input v-model="mgaSelectedKeys" type="checkbox" :value="opt.key" :disabled="statsStore.mgaRunning" />
                <span>{{ opt.predictor }} → {{ opt.outcome }}</span>
              </label>
            </div>
          </div>

          <div class="action-row">
            <button :class="BTN.primary" :disabled="statsStore.mgaRunning || !canRunMgaStructural" @click="runMgaStructural">
              {{ statsStore.mgaRunning ? `比较中…${statsStore.mgaTaskProgress || 0}%` : '运行 逐步比较（层级×路径）' }}
            </button>
          </div>
          <div
            v-if="mgaFeedback"
            :class="[FEEDBACK.base, resolveFeedbackTone(mgaFeedback.kind), 'mga-feedback']"
          >
            <p :class="FEEDBACK.text">{{ mgaFeedback.text }}</p>
            <p :class="FEEDBACK.detail">{{ mgaFeedback.detail }}</p>
          </div>

          <div v-if="mgaItems.length" class="est-table-wrap" style="margin-top: 0.65rem;">
            <div v-for="(it, idx) in mgaItems" :key="`mga-it-${idx}`" style="margin-top: 0.75rem;">
              <div class="inv-report-top" style="margin-bottom: 0.35rem;">
                <div class="inv-report-title">{{ it.levelLabel }} · {{ it.predictor }} → {{ it.outcome }}</div>
              </div>

              <table class="est-table">
                <thead>
                  <tr>
                    <th>组别</th>
                    <th>Estimate</th>
                    <th>Std.All</th>
                    <th>p</th>
                    <th>说明</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(r, j) in it.rows" :key="`mga-r-${idx}-${j}`">
                    <td>{{ r.group }}</td>
                    <td>{{ fmt(r.estimate) }}</td>
                    <td>{{ fmt(r.std_all) }}</td>
                    <td>{{ fmtP(r.p_value) }}</td>
                    <td>{{ r.note || '—' }}</td>
                  </tr>
                </tbody>
              </table>

              <table v-if="it.comparison" class="est-table" style="margin-top: 0.55rem;">
                <thead>
                  <tr>
                    <th>From</th>
                    <th>To</th>
                    <th>Δχ²</th>
                    <th>Δdf</th>
                    <th>p</th>
                    <th>note</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>{{ it.comparison.from || '—' }}</td>
                    <td>{{ it.comparison.to || '—' }}</td>
                    <td>{{ fmt(it.comparison.chi2_diff) }}</td>
                    <td>{{ fmt(it.comparison.df_diff) }}</td>
                    <td>{{ fmtP(it.comparison.p_value) }}</td>
                    <td>{{ it.comparison.note || '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section class="section reveal" :style="{ transitionDelay: '120ms' }">
          <h3 class="section-label">EXPORT / 导出</h3>
          <div class="section-rule"></div>
          <div class="project-name-row">
            <label class="project-name-label osem-field-label" for="project-name-input">项目名 / Project</label>
            <input
              id="project-name-input"
              v-model.trim="projectName"
              :class="[INP.input, 'project-name-input']"
              type="text"
              placeholder="OpenSEM"
              maxlength="48"
            />
          </div>
          <div class="export-actions">
            <button :class="BTN.ghost" :disabled="!canExportApa || exportingApaXlsx" @click="exportApaXlsx">
              <span class="btn-icon">📄</span>
              {{ exportingApaXlsx ? '导出中…' : 'APA 7th 表格 · .xlsx' }}
            </button>
            <button :class="BTN.ghost" :disabled="!canExportApa || exportingApaDocx" @click="exportApaDocx">
              <span class="btn-icon">📝</span>
              {{ exportingApaDocx ? '导出中…' : 'APA 7th 报告 · .docx' }}
            </button>
            <button :class="BTN.ghost" :disabled="!canExportSyntax || exportingSyntax" @click="exportLavaanSyntax">
              <span class="btn-icon">{ }</span>
              {{ exportingSyntax ? '导出中…' : 'lavaan 语法 · R' }}
            </button>
          </div>
          <p v-if="!canExportSyntax" class="export-hint">请先在建模页生成 lavaan 语法后再导出。</p>
          <div v-else-if="isFitStale" class="export-hint">
            <p style="margin: 0;">
              检测到语法已修改：当前拟合度/参数表可能对应旧版本。推荐先重新估算后再导出。
            </p>
            <label class="export-stale-toggle">
              <input v-model="allowStaleExport" type="checkbox" />
              <span>允许导出过期结果（后端将放行，但会在导出 Meta/报告中标注 STALE）</span>
            </label>
          </div>
          <p v-else-if="!canExportApa" class="export-hint">APA 导出需要先运行一次 ML 估算。</p>
          <p v-if="toastMessage" class="export-success">{{ toastMessage }}</p>
        </section>
      </main>

      <aside class="sidebar">
        <section class="sidebar-section osem-surface reveal" :style="{ transitionDelay: '80ms' }">
          <h3 class="sidebar-label">INTERPRETATION</h3>
          <div class="interpret-box">
            <p v-for="item in interpretationLines" :key="item">{{ item }}</p>
          </div>
        </section>
        <section
          class="sidebar-section reveal"
          :class="DENSE.zone"
          :style="{ transitionDelay: '160ms' }"
        >
          <h3 class="sidebar-label">MI SUGGESTIONS</h3>
          <p class="sidebar-tip">{{ miMessage }}</p>
          <div v-if="miSupported && miItems.length" class="mi-toolbar">
            <span class="mi-count">候选 {{ visibleMiItems.length }} / {{ miItems.length }}</span>
            <select
              v-model="miRiskFilter"
              :class="INP.selectCompact"
              aria-label="MI 建议筛选"
            >
              <option value="all">全部建议</option>
              <option value="low_first">优先低风险</option>
              <option value="high_only">仅看高风险</option>
            </select>
          </div>
          <div v-if="miAdoptionCountForTag" class="mi-toolbar" style="margin-top: 0.35rem;">
            <span class="mi-count">已采纳 {{ miAdoptionCountForTag }} 条（当前语法版本）</span>
            <button
              type="button"
              class="mi-apply-link"
              :aria-expanded="miAdoptions.length ? showAdoptions : undefined"
              @click="showAdoptions = !showAdoptions"
            >
              {{ showAdoptions ? '收起采纳记录' : '查看采纳记录' }}
            </button>
          </div>
          <div
            v-if="showAdoptions && miAdoptions.length"
            id="mi-adoptions-panel"
            class="mi-adoptions"
            role="region"
            aria-label="已采纳的 MI 修改记录"
          >
            <div v-for="rec in miAdoptions.slice(0, 8)" :key="rec.id" class="mi-adopt-item">
              <div class="mi-formula">{{ rec.mi_item_snapshot?.lhs }} {{ rec.mi_item_snapshot?.op }} {{ rec.mi_item_snapshot?.rhs }}</div>
              <div class="mi-meta">
                {{ rec.applied_to }} · {{ rec.applied_at }} · {{ rec.before_syntax_fingerprint }} → {{ rec.after_syntax_fingerprint }}
              </div>
              <div v-if="rec.notes" class="mi-text">{{ rec.notes }}</div>
              <div class="mi-item-actions" style="margin-top: 0.35rem;">
                <button
                  type="button"
                  class="mi-apply-btn mi-ignore-btn"
                  :disabled="Boolean(rec.undone_at)"
                  @click="undoMiAdoption(rec)"
                >
                  {{ rec.undone_at ? '已撤销' : '撤销（回滚语法）' }}
                </button>
                <span v-if="rec.undone_at" class="mi-meta" style="margin-left: 0.5rem;">
                  撤销时间：{{ rec.undone_at }}
                </span>
              </div>
            </div>
            <button
              v-if="miAdoptions.length > 8"
              type="button"
              class="mi-apply-link mi-apply-link-block"
              @click="copyText(JSON.stringify(miAdoptions, null, 2), '已复制采纳记录（JSON）')"
            >
              复制全部采纳记录（JSON）
            </button>
          </div>
          <p v-if="modelStore.miAdoptionCount >= 3" class="mi-warning">
            过拟合警告：您已累计采纳 {{ modelStore.miAdoptionCount }} 条 MI 修正建议。过度依赖 MI 可能导致模型过拟合，建议回到理论框架确认每条修正是否合理。
          </p>
          <div v-if="miSupported && miItems.length" class="mi-list">
            <div v-for="(it, idx) in visibleMiItems" :key="`mi-${idx}`" class="mi-item">
              <div class="mi-formula">{{ it.lhs }} {{ it.op }} {{ it.rhs }}</div>
              <div class="mi-meta">MI={{ fmt(it.mi) }} · EPC={{ fmt(it.epc) }}</div>
              <div class="mi-tags">
                <span class="mi-tag mi-tag-kind">{{ it.kindLabel }}</span>
                <span class="mi-tag" :class="`mi-tag-risk-${it.risk}`">风险{{ it.riskLabel }}</span>
              </div>
              <div class="mi-text">建议允许该路径/协变关系，预期可使 χ² 降低约 {{ fmt(it.mi) }}（请结合理论判断）。</div>
              <div class="mi-item-actions">
                <button type="button" class="mi-apply-btn" @click="applyMiToSyntax(it)">填入 lavaan 语法</button>
                <button type="button" class="mi-copy-btn" @click="copyMiLine(it)">复制该条</button>
                <button type="button" class="mi-apply-btn mi-apply-cta" @click="applyMiAndGo(it)">填入并前往建模</button>
                <button
                  v-if="miAutoRefitAllowed(it)"
                  type="button"
                  class="mi-apply-btn mi-apply-cta"
                  @click="applyMiAndRefit(it)"
                >
                  采纳并重算
                </button>
                <button
                  v-else
                  type="button"
                  class="mi-apply-btn mi-apply-cta"
                  @click="applyMiToSyntaxWithHint(it)"
                >
                  采纳到草稿
                </button>
                <button type="button" class="mi-apply-btn mi-ignore-btn" @click="ignoreMi(it)">忽略</button>
              </div>
              <p v-if="!miAutoRefitAllowed(it)" class="sidebar-tip mi-guard" style="margin: 0.35rem 0 0;">
                已禁用自动重估：{{ miAutoRefitReason(it) }}
              </p>
            </div>
            <button
              v-if="ignoredMiCount"
              type="button"
              class="mi-apply-link mi-apply-link-block"
              @click="toggleShowIgnored"
            >
              {{ showIgnored ? `隐藏已忽略（${ignoredMiCount}）` : `显示已忽略（${ignoredMiCount}）` }}
            </button>
            <button type="button" class="mi-apply-link mi-apply-link-block" @click="goModelAfterMi">前往建模页查看 / 调整语法</button>
          </div>
          <button :class="[BTN.ghost, 'mi-btn']" :disabled="miLoading || !canExportSyntax || !lavaanAvailable" @click="loadMi">
            {{ miLoading ? '获取中…' : '获取 MI 建议' }}
          </button>
          <p class="sidebar-tip mi-guard">
            过拟合防护：优先看理论是否支持该残差/协变；一次只考虑 1 条修正；MI 高不等于必须加路径。
          </p>
        </section>
      </aside>
    </div>

    <p class="status-hint reveal" :style="{ transitionDelay: '200ms' }">导出模块已支持 `.xlsx` / `.docx` / `.txt`</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api/client'
import { useDataStore } from '../stores/dataStore'
import { useModelStore } from '../stores/modelStore'
import { useStatsStore } from '../stores/statsStore'
import { useRuntimeStore } from '../stores/runtimeStore'
import { useMiAdoptionStore } from '../stores/miAdoptionStore'
import { useNoticeStore } from '../stores/noticeStore'
import { useDialogStore } from '../stores/dialogStore'
import SemGraph from '../components/SemGraph.vue'
import TermTip from '../components/TermTip.vue'
import { evaluateMiGuard } from '../mi/miGuard'
import { pushErrorNotice, pushWarningNotice, requestUserConfirm } from '../utils/uiFeedback'
import { buildPathSummaryReportText, buildPathSummaryRows } from './results/pathSummary'
import { inferMiKind, inferMiRisk } from './results/miRisk'
import { miKey } from './results/miKey'
import { normalizeMgaRows } from './results/normalizeMgaRows'
import { fmt, fmtCi, fmtP } from './results/formatters'
import { normalizeGate } from './results/gate'
import { buildInvOneLineConclusion } from './results/invConclusion'
import { computeInvSeriesConclusionLevel } from './results/invConclusionLevel'
import { buildInvSeriesCardText } from './results/invSeriesCards'
import { normalizeSyntax, shortTag } from './results/syntaxFingerprint'
import { normalizeSyntaxForCompare } from './results/normalizeSyntaxForCompare'
import { resolveBootstrapFeedback } from './results/bootstrapFeedback'
import { resolveModelCompareFeedback } from './results/modelCompareFeedback'
import { resolveInvarianceSeriesFeedback } from './results/invarianceSeriesFeedback'
import { resolveMgaFeedback } from './results/mgaFeedback'
import { parseMediatorChain } from './results/mediationDraft'
import { bootstrapEffectTypeLabel, fmtSequence } from './results/bootstrapDisplay'
import { toNum } from './results/toNum'
import { isNA } from './results/isNA'
import { explainFitMetric, formatFitMetricValue } from './results/fitIndicesMetric'
import { computeInvStepBadge } from './results/invStepBadge'
import { buildInvModelFitLine } from './results/invModelFitLine'
import { getFilenameFromHeaders } from './results/getFilenameFromHeaders'
import { formatInvModelMetric4 } from './results/invModelCardFormat'
import { parseBlobError } from './results/parseBlobError'
import { delegateShowToast } from './results/showToastDelegate'
import { formatDownloadBlobFilename } from './results/downloadBlobFilename'
import { delegateDownloadBlob } from './results/downloadBlobDelegate'
import { BTN } from '../ui/buttonContract.js'
import { INP } from '../ui/inputContract.js'
import { FEEDBACK, resolveFeedbackTone } from '../ui/feedbackContract.js'
import { resolveCorePageRhythm, toCorePageStyleVars } from './core/corePageRhythm'
import { DENSE, toDenseInlineStyleVars } from './results/resultsDenseContract'

const router = useRouter()
const dataStore = useDataStore()
const modelStore = useModelStore()
const statsStore = useStatsStore()
const runtimeStore = useRuntimeStore()
const miAdoptionStore = useMiAdoptionStore()
const noticeStore = useNoticeStore()
const dialogStore = useDialogStore()
const resultsPageStyle = {
  ...toCorePageStyleVars(resolveCorePageRhythm('results')),
  ...toDenseInlineStyleVars(),
}
const projectName = ref('OpenSEM')
const PROJECT_NAME_KEY = 'OpenSEM:project-name:v1'
const exportingApaXlsx = ref(false)
const exportingApaDocx = ref(false)
const exportingSyntax = ref(false)
const allowStaleExport = ref(false)
const toastMessage = ref('')
let toastTimer = null

const canFit = computed(() => Boolean(dataStore.dataKey && modelStore.lavaanSyntax))
const needsMissingStrategy = computed(() => Boolean(dataStore.highMissingWarning && !dataStore.missingStrategy))
const canExportSyntax = computed(() => Boolean(dataStore.dataKey && modelStore.lavaanSyntax))
const fitStatusFeedback = computed(() => {
  if (statsStore.fitting) {
    return {
      kind: 'loading',
      text: '估算任务运行中…',
      detail: statsStore.taskMessage || '请稍候，任务完成后将自动刷新拟合度与参数估计。',
    }
  }
  if (!canFit.value) {
    return {
      kind: 'empty',
      text: '当前无可估算模型',
      detail: '请先在建模页生成 lavaan 语法后再估算。',
    }
  }
  if (needsMissingStrategy.value) {
    return {
      kind: 'warning',
      text: '估算前需要先确认缺失值处理方案',
      detail: '检测到缺失率 > 5%，请先在数据管理页选择缺失值处理方案。',
    }
  }
  if (statsStore.error) {
    return {
      kind: 'error',
      text: statsStore.error,
      detail: statsStore.errorHint || '请检查模型语法、数据会话与参数配置后重试。',
    }
  }
  return null
})

const lavaanAvailable = computed(() => Boolean(runtimeStore.lavaanAvailable))
const lavaanGateText = computed(() => String(runtimeStore.lavaanMessage || '').trim())

const currentSyntaxNorm = computed(() => normalizeSyntax(modelStore.lavaanSyntax))
const currentSyntaxTag = computed(() => (currentSyntaxNorm.value ? shortTag(currentSyntaxNorm.value) : '—'))
const lastFitSyntaxTag = computed(() => (statsStore.lastFitSyntaxNorm ? shortTag(statsStore.lastFitSyntaxNorm) : '—'))
const lastFitAtText = computed(() => {
  const raw = statsStore.lastFitAt
  if (!raw) return '—'
  try {
    const d = new Date(raw)
    if (!Number.isFinite(d.getTime())) return String(raw)
    return d.toLocaleString()
  } catch (_) {
    return String(raw)
  }
})

const isFitStale = computed(() => {
  if (!statsStore.fitIndices) return false
  const current = currentSyntaxNorm.value
  const last = String(statsStore.lastFitSyntaxNorm || '')
  if (!last) return false
  return current !== last
})

const canExportApa = computed(() =>
  Boolean(canExportSyntax.value && statsStore.fitIndices && (!isFitStale.value || allowStaleExport.value))
)

const localEstimator = ref(statsStore.estimator || 'ML')
const localMissingStrategy = ref(dataStore.missingStrategy || statsStore.missingStrategy || 'listwise')

const variableNames = computed(() => (dataStore.variables || []).map((v) => v.name).filter(Boolean))
const medDraftX = ref('')
const medDraftChain = ref('')
const medDraftY = ref('')
const mediationEffects = ref([])
const bootN = ref(2000)
const bootCovariatesText = ref('')
const groupVar = ref('')
const modX = ref('')
const modW = ref('')
const modY = ref('')
const modCovariatesText = ref('')
const modType = ref('continuous')
const mmX = ref('')
const mmM = ref('')
const mmY = ref('')
const mmW = ref('')
const mmHayesModel = ref('7')
const mmWType = ref('continuous')
const mmBootN = ref(2000)
const mmCovariatesText = ref('')

watch(mmHayesModel, (v) => {
  if (v === '14') mmWType.value = 'continuous'
})

const compareLabelA = ref('Model A')
const compareLabelB = ref('Model B')
const compareSyntaxB = ref('')
const mgaPredictor = ref('')
const mgaOutcome = ref('')
const mgaSelectedKeys = ref([])
const canAddMediationEffect = computed(() => Boolean(medDraftX.value && medDraftChain.value && medDraftY.value))
const canRunBootstrap = computed(() => Boolean(mediationEffects.value.length))
const bootstrapFeedback = computed(() =>
  resolveBootstrapFeedback({
    bootstrapping: Boolean(statsStore.bootstrapping),
    bootstrapTaskMessage: statsStore.bootstrapTaskMessage,
    bootstrapError: statsStore.bootstrapError,
    bootstrapErrorHint: statsStore.bootstrapErrorHint,
    bootstrapResultItemsCount: Array.isArray(statsStore.bootstrapResult?.items) ? statsStore.bootstrapResult.items.length : 0,
  })
)
const invarianceSeriesFeedback = computed(() =>
  resolveInvarianceSeriesFeedback({
    invarianceSeriesRunning: Boolean(statsStore.invarianceSeriesRunning),
    invarianceSeriesTaskMessage: statsStore.invarianceSeriesTaskMessage,
    invarianceSeriesError: statsStore.invarianceSeriesError,
    invarianceSeriesErrorHint: statsStore.invarianceSeriesErrorHint,
    invarianceSeriesModelsCount: Array.isArray(statsStore.invarianceSeriesResult?.models)
      ? statsStore.invarianceSeriesResult.models.length
      : 0,
  })
)
const canRunModeration = computed(() => Boolean(canFit.value && modX.value && modW.value && modY.value))
const canRunModeratedMediation = computed(() => {
  if (!canFit.value) return false
  const a = [mmX.value, mmM.value, mmY.value, mmW.value].map((s) => String(s || '').trim())
  if (a.some((s) => !s)) return false
  return new Set(a).size === 4
})
const canRunModelCompare = computed(() =>
  Boolean(canFit.value && dataStore.dataKey && modelStore.lavaanSyntax && String(compareSyntaxB.value || '').trim())
)
const modelCompareFeedback = computed(() =>
  resolveModelCompareFeedback({
    modelCompareRunning: Boolean(statsStore.modelCompareRunning),
    modelCompareTaskMessage: statsStore.modelCompareTaskMessage,
    modelCompareError: statsStore.modelCompareError,
    modelCompareErrorHint: statsStore.modelCompareErrorHint,
    modelCompareModelsCount: Array.isArray(statsStore.modelCompareResult?.models)
      ? statsStore.modelCompareResult.models.length
      : 0,
  })
)
const mgaPathOptions = computed(() => {
  const est = Array.isArray(statsStore.estimates) ? statsStore.estimates : []
  const seen = new Set()
  const out = []
  for (const r of est) {
    if (!r || typeof r !== 'object') continue
    const op = String(r.op || '').trim()
    if (op !== '~') continue
    const outcome = String(r.lval || '').trim()
    const predictor = String(r.rval || '').trim()
    if (!outcome || !predictor) continue
    const key = `${predictor}→${outcome}`
    if (seen.has(key)) continue
    seen.add(key)
    out.push({ key, predictor, outcome })
  }
  return out
})

watch(
  mgaPathOptions,
  (opts) => {
    if (!Array.isArray(opts) || !opts.length) return
    if (Array.isArray(mgaSelectedKeys.value) && mgaSelectedKeys.value.length) return
    mgaSelectedKeys.value = opts.map((x) => x.key)
  },
  { immediate: true }
)

const mgaChosenPaths = computed(() => {
  const keys = new Set(Array.isArray(mgaSelectedKeys.value) ? mgaSelectedKeys.value : [])
  return mgaPathOptions.value.filter((x) => keys.has(x.key))
})

const canRunMgaStructural = computed(() =>
  Boolean(canFit.value && dataStore.dataKey && modelStore.lavaanSyntax && groupVar.value && mgaChosenPaths.value.length)
)

const mgaItems = computed(() => {
  const r = statsStore.mgaResult
  if (!r || typeof r !== 'object') return []
  const out = []
  if (Array.isArray(r.items) && r.items.length) {
    for (const it of r.items) {
      if (!it || typeof it !== 'object') continue
      const level = String(it.level || '').trim()
      const p = it.path && typeof it.path === 'object' ? it.path : {}
      const predictor = String(p.predictor || '').trim()
      const outcome = String(p.outcome || '').trim()
      out.push({
        level,
        levelLabel: level ? `Level=${level}` : 'Level=—',
        predictor: predictor || '—',
        outcome: outcome || '—',
        rows: normalizeMgaRows(it.group_estimates),
        comparison: it.comparison && typeof it.comparison === 'object' ? it.comparison : null,
      })
    }
    return out
  }
  // 旧结构：单路径
  const p = r.path && typeof r.path === 'object' ? r.path : {}
  out.push({
    level: '',
    levelLabel: 'Level=—',
    predictor: String(p.predictor || '').trim() || String(r.predictor || '').trim() || '—',
    outcome: String(p.outcome || '').trim() || String(r.outcome || '').trim() || '—',
    rows: normalizeMgaRows(r.group_estimates),
    comparison: r.comparison && typeof r.comparison === 'object' ? r.comparison : null,
  })
  return out
})

const mgaFeedback = computed(() =>
  resolveMgaFeedback({
    mgaRunning: Boolean(statsStore.mgaRunning),
    mgaTaskMessage: statsStore.mgaTaskMessage,
    mgaError: statsStore.mgaError,
    mgaErrorHint: statsStore.mgaErrorHint,
    mgaItemsCount: mgaItems.value.length,
    mgaResultMessage: String(statsStore.mgaResult?.message || '').trim(),
  })
)

const statusText = computed(() => {
  const status = statsStore.fitIndices?.status
  if (status === 'good') return '拟合良好（绿灯）'
  if (status === 'poor') return '拟合较差（红灯）'
  if (status === 'borderline') return '拟合临界（黄灯）'
  return ''
})

const interpretationLines = computed(() => {
  const fit = statsStore.fitIndices
  if (!fit) {
    return ['请先运行 ML 估算', 'CFI >= 0.90 通常视为可接受', 'RMSEA / SRMR < 0.08 通常可接受']
  }
  const lines = []
  if (fit.cfi !== '-' && fit.cfi !== undefined) {
    lines.push(Number(fit.cfi) >= 0.9 ? `CFI=${fit.cfi}，模型比较拟合较好` : `CFI=${fit.cfi}，模型比较拟合偏弱`)
  }
  if (fit.rmsea !== '-' && fit.rmsea !== undefined) {
    lines.push(Number(fit.rmsea) < 0.08 ? `RMSEA=${fit.rmsea}，近似误差可接受` : `RMSEA=${fit.rmsea}，近似误差偏高`)
  }
  if (fit.srmr !== '-' && fit.srmr !== undefined) {
    lines.push(Number(fit.srmr) < 0.08 ? `SRMR=${fit.srmr}，残差表现可接受` : `SRMR=${fit.srmr}，残差表现偏高`)
  }
  lines.push(
    fit.status === 'good'
      ? '综合判断：绿灯，可进入结果报告阶段'
      : fit.status === 'poor'
        ? '综合判断：红灯，建议回到建模页调整路径'
        : '综合判断：黄灯，建议结合理论与MI进一步修正'
  )
  return lines
})

const pathSummaryRows = computed(() => buildPathSummaryRows(statsStore.estimates))

const pathSummaryLines = computed(() => {
  if (!statsStore.estimates?.length) return []
  const rows = pathSummaryRows.value || []
  if (!rows.length) return ["提示：未识别到可汇总的结构回归路径（op='~' 且含 p 值）。"]
  const sig = rows.filter((r) => r.significant)
  return [
    "汇总口径：仅统计结构回归路径（op='~'），显著性门槛 p<0.05；β 优先使用标准化估计（Est. Std）。",
    `本次识别到回归路径 ${rows.length} 条，其中显著 ${sig.length} 条。`,
    sig.length ? `显著路径示例（按 |β| 排序，最多 5 条）：${sig.slice(0, 5).map((r) => `${r.predictor}→${r.outcome}(β=${fmt(r.beta)},p=${fmtP(r.p_value)})`).join('；')}` : "当前无显著结构路径（p<0.05）。",
  ]
})

const pathSummaryReportText = computed(() => {
  if (!statsStore.estimates?.length) return ''
  return buildPathSummaryReportText({
    estimates: statsStore.estimates,
    nUsed: statsStore.nUsed,
  })
})

const integratedPaperParagraph = computed(() => {
  const hasFit = Boolean(statsStore.fitIndices)
  const hasPath = (pathSummaryRows.value || []).length > 0
  const br = statsStore.bootstrapResult
  const hasBoot =
    br &&
    Array.isArray(br.items) &&
    br.items.some((it) => it && (it.effect_type === 'specific_indirect' || it.effect_type === 'total_indirect'))
  const mm = statsStore.moderatedMediationResult
  const hasMm = mm && Array.isArray(mm.conditional_indirect) && mm.conditional_indirect.length
  const mod = statsStore.moderationResult
  const hasMod = mod && ((mod.coefficients && mod.coefficients.length) || (mod.simple_slopes && mod.simple_slopes.length))
  if (!hasFit && !hasPath && !hasBoot && !hasMm && !hasMod) {
    return ''
  }

  const lines = []
  lines.push('【综合结果摘要（自动生成，论文段落草案；请按期刊要求改写）】')
  const n = Number(statsStore.nUsed || 0)
  const estLabel = statsStore.estimator || 'ML'
  if (n) {
    lines.push(`本研究采用结构方程模型，使用 ${estLabel} 估计；有效样本量 N=${n}。`)
  } else {
    lines.push('（尚未记录有效样本量：请先运行 ML 估算以写入 N。）')
  }

  const fit = statsStore.fitIndices
  if (fit) {
    const bits = []
    if (fit.chi2 !== '-' && fit.chi2 !== undefined) bits.push(`χ²=${fit.chi2}`)
    if (fit.cfi !== '-' && fit.cfi !== undefined) bits.push(`CFI=${fit.cfi}`)
    if (fit.tli !== '-' && fit.tli !== undefined) bits.push(`TLI=${fit.tli}`)
    if (fit.rmsea !== '-' && fit.rmsea !== undefined) bits.push(`RMSEA=${fit.rmsea}`)
    if (fit.srmr !== '-' && fit.srmr !== undefined) bits.push(`SRMR=${fit.srmr}`)
    if (bits.length) {
      const st = statusText.value ? `${statusText.value}。` : ''
      lines.push(`整体拟合指标：${bits.join('，')}。${st}`)
    }
  }

  if (pathSummaryReportText.value) {
    lines.push('')
    lines.push('结构路径（摘录）：')
    lines.push(pathSummaryReportText.value)
  }

  if (hasBoot && br?.items) {
    const indirects = br.items.filter(
      (it) => it && (it.effect_type === 'specific_indirect' || it.effect_type === 'total_indirect')
    )
    if (indirects.length) {
      lines.push('')
      lines.push('Bootstrap 中介（节选）：')
      const maxShow = 5
      for (const it of indirects.slice(0, maxShow)) {
        const lab = it.label || (Array.isArray(it.sequence) ? it.sequence.join('→') : it.path_label || '效应')
        const pt = it.indirect_point != null && Number.isFinite(Number(it.indirect_point)) ? Number(it.indirect_point).toFixed(4) : '—'
        let ciStr = ''
        const c = it.ci
        if (c && typeof c === 'object' && c.percentile && c.percentile.lo != null && c.percentile.hi != null) {
          ciStr = `，95% CI=[${Number(c.percentile.lo).toFixed(4)}, ${Number(c.percentile.hi).toFixed(4)}]（percentile）`
        }
        lines.push(`- ${lab}：间接效应=${pt}${ciStr}`)
      }
      if (indirects.length > maxShow) {
        lines.push(`（另有 ${indirects.length - maxShow} 条间接效应，详见 Bootstrap 表）`)
      }
    }
  }

  if (hasMm && mm) {
    lines.push('')
    const hm = String(mm.hayes_model ?? '').trim()
    const modelLab = mm.model || (hm === '14' ? 'Hayes Model 14' : 'Hayes Model 7')
    lines.push(
      `有调节的中介（${modelLab}）：Bootstrap 次数=${mm.n_boot ?? '—'}；条件间接效应（节选）如下。`
    )
    for (const row of (mm.conditional_indirect || []).slice(0, 5)) {
      const label = row.label || row.w_value || row.contrast || '—'
      const ind = row.indirect_point != null ? String(row.indirect_point) : '—'
      lines.push(`- ${label}：间接效应=${ind}`)
    }
  }

  if (hasMod) {
    lines.push('')
    lines.push(
      '观测变量调节：已估计交互项与简单斜率（详见「调节分析」表）；报告时请写明调节变量类型与简单斜率比较口径。'
    )
  }

  lines.push('')
  lines.push('（说明：显著性门槛、效应量与句式请按目标期刊/APA 人工核对。）')
  return lines.join('\n')
})

const bootstrapFxBridgeLines = computed(() => {
  const items = statsStore.bootstrapResult?.items || []
  const lines = []
  for (const r of items) {
    if (!r || (r.effect_type !== 'direct_effect' && r.effect_type !== 'total_effect')) continue
    const lab = r.effect_type === 'direct_effect' ? '直接效应' : '总效应'
    const pt = fmt(r.indirect_point)
    const note = r.note ? ` ${r.note}` : ''
    lines.push(`${lab}（${r.x}→${r.y}）：${pt}${note}`)
  }
  return lines
})

const liProbeY = ref('Y')
const liProbeF1 = ref('F1')
const liProbeF2 = ref('F2')

const canRunLatentInteractionProbe = computed(() => {
  if (!canFit.value) return false
  const a = [liProbeY.value, liProbeF1.value, liProbeF2.value].map((s) => String(s || '').trim())
  if (a.some((s) => !s)) return false
  return new Set(a).size === 3
})

const miMessage = computed(() => {
  if (!dataStore.dataKey || !modelStore.lavaanSyntax) return '请先上传数据并生成 lavaan 语法'
  if (!lavaanAvailable.value) return lavaanGateText.value || '当前环境未启用 lavaan，MI 不可用。'
  if (miLoading.value) return '正在请求 MI…'
  if (miSupported.value && miItems.value.length) return '以下为 MI 候选项（请结合理论，避免过拟合）'
  return miHint.value || '点击“获取 MI 建议”尝试从后端获取（若当前环境未启用 lavaan，会返回占位提示）。'
})

const invSeriesGate = computed(() =>
  normalizeGate(statsStore.invarianceSeriesResult, {
    supported: lavaanAvailable.value,
    fallbackMessageWhenDegraded: '当前环境未启用 lavaan：不变性序列已降级/不可用，可改用“多群组(配置)”方案。',
  })
)

const invSeriesSummaryLines = computed(() => {
  const r = statsStore.invarianceSeriesResult
  if (!r || !Array.isArray(r.comparisons) || !r.comparisons.length) return []
  if (invSeriesGate.value?.degraded) {
    return ['提示：当前为降级结果，不能作为 metric/scalar/strict 的等值检验结论。']
  }

  const CFI_TH = 0.01
  const RMSEA_TH = 0.015

  const lines = [
    `建议（常用经验阈值）：|ΔCFI| < ${CFI_TH} 且 |ΔRMSEA| < ${RMSEA_TH} 时，通常可认为该步等值约束“可接受”。大样本下不要只看 Δχ² 的 p 值。`,
  ]

  for (const c of r.comparisons) {
    const from = String(c?.from || '').trim()
    const to = String(c?.to || '').trim()
    const dcfi = toNum(c?.delta_cfi)
    const drmsea = toNum(c?.delta_rmsea)
    const has = dcfi !== null && drmsea !== null
    const ok = has ? Math.abs(dcfi) < CFI_TH && Math.abs(drmsea) < RMSEA_TH : null
    const label = from && to ? `${from}→${to}` : '—'
    if (ok === true) {
      lines.push(`${label}：PASS（|ΔCFI|=${Math.abs(dcfi).toFixed(4)}，|ΔRMSEA|=${Math.abs(drmsea).toFixed(4)}）`)
    } else if (ok === false) {
      lines.push(`${label}：FAIL（|ΔCFI|=${Math.abs(dcfi).toFixed(4)}，|ΔRMSEA|=${Math.abs(drmsea).toFixed(4)}）`)
    } else {
      lines.push(`${label}：—（缺少 ΔCFI/ΔRMSEA，无法给出经验阈值判断）`)
    }
  }
  return lines
})

function invStepBadge(c) {
  return computeInvStepBadge(c, { degraded: !!invSeriesGate.value?.degraded })
}

const invSeriesCards = computed(() => {
  const r = statsStore.invarianceSeriesResult
  if (!r || !Array.isArray(r.comparisons) || !r.comparisons.length) return []

  const cards = []
  for (const c of r.comparisons) {
    const from = String(c?.from || '').trim()
    const to = String(c?.to || '').trim()
    const label = from && to ? `${from} → ${to}` : '—'
    const b = invStepBadge(c)

    const cardText = buildInvSeriesCardText({
      comparison: c,
      badge: b.badge,
      degraded: !!invSeriesGate.value?.degraded,
      fmtP,
      isNA,
    })

    cards.push({
      title: `逐步结论：${label}`,
      badge: b.badge,
      status: b.status,
      threshold: cardText.threshold,
      evidence: cardText.evidence,
      reason: b.badge === '—' && !invSeriesGate.value?.degraded
        ? String(b.note || cardText.reason)
        : cardText.reason,
    })
  }
  return cards
})

function invSeriesConclusionLevel({ lite = false } = {}) {
  const r = statsStore.invarianceSeriesResult
  return computeInvSeriesConclusionLevel({
    lite,
    degraded: !r || !!invSeriesGate.value?.degraded,
    comparisons: r?.comparisons,
    getStepBadge: (c) => invStepBadge(c),
  })
}

const invSeriesConclusion = computed(() => {
  return {
    strict: invSeriesConclusionLevel({ lite: false }),
    lite: invSeriesConclusionLevel({ lite: true }),
  }
})

function _reportOneLineConclusion({ lite = false } = {}) {
  const c = invSeriesConclusion.value?.[lite ? 'lite' : 'strict'] || {}
  return buildInvOneLineConclusion({ conclusion: c, lite })
}

const invSeriesReportTextStrict = computed(() => {
  const r = statsStore.invarianceSeriesResult
  if (!r || invSeriesGate.value?.degraded) return ''
  if (!Array.isArray(r.models) || !Array.isArray(r.comparisons) || !r.comparisons.length) return ''

  const CFI_TH = 0.01
  const RMSEA_TH = 0.015

  const modelFitLine = (name) => buildInvModelFitLine({ name, models: r.models, toNum })

  const lines = []
  lines.push('【测量不变性检验（多群组）报告模板】')
  lines.push('本研究采用 lavaan 进行多群组测量不变性（configural→metric→scalar→strict）序列检验。')
  lines.push(
    `判定原则采用常用经验阈值：当相邻模型的拟合度变化满足 |ΔCFI|<${CFI_TH} 且 |ΔRMSEA|<${RMSEA_TH} 时，通常认为该步等值约束可接受；在大样本条件下不建议仅依据 Δχ² 的显著性作结论。`
  )
  lines.push('')
  lines.push('【模型拟合（各步）】')
  lines.push(modelFitLine('configural'))
  lines.push(modelFitLine('metric'))
  lines.push(modelFitLine('scalar'))
  lines.push(modelFitLine('strict'))
  lines.push('')
  lines.push('【相邻模型比较（逐步结论）】')

  for (const c of r.comparisons) {
    const from = String(c?.from || '').trim()
    const to = String(c?.to || '').trim()
    const label = from && to ? `${from}→${to}` : '—'
    const b = invStepBadge(c)
    if (b.badge === '—') {
      lines.push(`${label}：不可判定（${b.note || '缺少关键指标'}）`)
    } else {
      lines.push(`${label}：${b.badge}（${b.note || '—'}）`)
    }
  }

  lines.push('')
  lines.push('【一句话结论（可直接放摘要/讨论）】')
  lines.push(_reportOneLineConclusion({ lite: false }))

  return lines.join('\n')
})

const invSeriesReportTextLite = computed(() => {
  const r = statsStore.invarianceSeriesResult
  if (!r || invSeriesGate.value?.degraded) return ''
  if (!Array.isArray(r.models) || !Array.isArray(r.comparisons) || !r.comparisons.length) return ''

  const CFI_TH = 0.01
  const RMSEA_TH = 0.015

  const modelFitLine = (name) => buildInvModelFitLine({ name, models: r.models, toNum })

  // lite：常用报告到 scalar（很多论文只要求到 scalar）
  const keepComparisons = new Set(['configural→metric', 'metric→scalar'])
  const lines = []
  lines.push('【测量不变性检验（多群组）报告模板（lite）】')
  lines.push('本研究采用 lavaan 进行多群组测量不变性序列检验（lite：configural→metric→scalar）。')
  lines.push(
    `判定原则采用常用经验阈值：当相邻模型的拟合度变化满足 |ΔCFI|<${CFI_TH} 且 |ΔRMSEA|<${RMSEA_TH} 时，通常认为该步等值约束可接受；在大样本条件下不建议仅依据 Δχ² 的显著性作结论。`
  )
  lines.push('')
  lines.push('【模型拟合（各步）】')
  lines.push(modelFitLine('configural'))
  lines.push(modelFitLine('metric'))
  lines.push(modelFitLine('scalar'))
  lines.push('')
  lines.push('【相邻模型比较（逐步结论）】')
  for (const c of r.comparisons) {
    const from = String(c?.from || '').trim()
    const to = String(c?.to || '').trim()
    const label = from && to ? `${from}→${to}` : '—'
    if (!keepComparisons.has(`${from}→${to}`)) continue
    const b = invStepBadge(c)
    if (b.badge === '—') lines.push(`${label}：不可判定（${b.note || '缺少关键指标'}）`)
    else lines.push(`${label}：${b.badge}（${b.note || '—'}）`)
  }
  lines.push('')
  lines.push('【一句话结论（可直接放摘要/讨论）】')
  lines.push(_reportOneLineConclusion({ lite: true }))
  return lines.join('\n')
})

const invModelCards = computed(() => {
  const r = statsStore.invarianceSeriesResult
  if (!r || invSeriesGate.value?.degraded) return []
  const models = Array.isArray(r.models) ? r.models : []
  if (!models.length) return []

  const cards = []
  for (const m of models) {
    const name = String(m?.model || '').trim() || '—'
    const fit = m?.fit && typeof m.fit === 'object' ? m.fit : {}
    const cfi = toNum(fit.cfi)
    const tli = toNum(fit.tli)
    const rmsea = toNum(fit.rmsea)
    const srmr = toNum(fit.srmr)
    const chi2 = toNum(fit.chi2)
    const df = toNum(fit.df)
    const converged = m.converged

    const badge = converged === false ? '未收敛' : converged === true ? '收敛' : '未知'
    const status = converged === false ? 'fail' : converged === true ? 'pass' : 'unknown'

    cards.push({
      title: `模型：${name}`,
      badge,
      status,
      convergedText: badge,
      cfiTli: `CFI=${formatInvModelMetric4(cfi)} · TLI=${formatInvModelMetric4(tli)}`,
      rmseaSrmr: `RMSEA=${formatInvModelMetric4(rmsea)} · SRMR=${formatInvModelMetric4(srmr)}`,
      chi2Df: `χ²=${chi2 === null ? 'NA' : chi2.toFixed(3)} · df=${df === null ? 'NA' : df.toFixed(0)}`,
    })
  }
  return cards
})

const miLoading = ref(false)
const miSupported = ref(false)
const miItems = ref([])
const miHint = ref('')
const showIgnored = ref(false)
const ignoredMiKeys = ref(new Set())
const miRiskFilter = ref('all')

const ignoredMiStorageKey = computed(() => `OpenSEM:mi:ignored:v1:${currentSyntaxTag.value}`)

function loadIgnoredMi() {
  ignoredMiKeys.value = new Set()
  try {
    const raw = localStorage.getItem(ignoredMiStorageKey.value)
    if (!raw) return
    const arr = JSON.parse(raw)
    if (Array.isArray(arr)) ignoredMiKeys.value = new Set(arr.map(String))
  } catch (_) {
    // ignore
  }
}

function saveIgnoredMi() {
  try {
    localStorage.setItem(ignoredMiStorageKey.value, JSON.stringify(Array.from(ignoredMiKeys.value)))
  } catch (_) {
    // ignore
  }
}

const ignoredMiCount = computed(() => ignoredMiKeys.value.size)

const miAdoptions = computed(() => {
  // bucket by 当前语法版本（tag）
  return miAdoptionStore.getForTag(currentSyntaxTag.value) || []
})
const miAdoptionCountForTag = computed(() => miAdoptions.value.length)
const showAdoptions = ref(false)

const enrichedMiItems = computed(() => {
  const items = Array.isArray(miItems.value) ? miItems.value : []
  return items.map((it) => {
    const kind = inferMiKind(it)
    const risk = inferMiRisk(it, items)
    return {
      ...it,
      kind: kind.kind,
      kindLabel: kind.label,
      risk: risk.risk,
      riskLabel: risk.label,
    }
  })
})

const visibleMiItems = computed(() => {
  let items = enrichedMiItems.value || []
  if (miRiskFilter.value === 'high_only') {
    items = items.filter((it) => it.risk === 'high')
  } else if (miRiskFilter.value === 'low_first') {
    const rank = { low: 0, medium: 1, high: 2 }
    items = [...items].sort((a, b) => (rank[a.risk] ?? 9) - (rank[b.risk] ?? 9))
  }
  if (showIgnored.value) return items
  const ignored = ignoredMiKeys.value
  return items.filter((it) => !ignored.has(miKey(it)))
})

function ignoreMi(it) {
  const k = miKey(it)
  if (!k || k === '::::') return
  ignoredMiKeys.value.add(k)
  saveIgnoredMi()
  showToast('已忽略该条 MI（可在下方切换显示）')
}

function toggleShowIgnored() {
  showIgnored.value = !showIgnored.value
}

function metric(key) {
  return formatFitMetricValue(key, statsStore.fitIndices)
}

function explainMetric(key) {
  return explainFitMetric(key, statsStore.fitIndices)
}

function addMediationEffect() {
  const mediators = parseMediatorChain(medDraftChain.value)
  if (!medDraftX.value || !medDraftY.value || !mediators.length) {
    pushWarningNotice(noticeStore, '请至少选择 X、Y，并填写一个或多个中介变量')
    return
  }
  const sequence = [medDraftX.value, ...mediators, medDraftY.value]
  const duplicate = mediationEffects.value.some((item) => JSON.stringify(item.sequence) === JSON.stringify(sequence))
  if (duplicate) {
    showToast('该路径已添加，无需重复录入')
    return
  }
  mediationEffects.value.push({
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    sequence,
    label: sequence.join(' → '),
  })
  medDraftChain.value = ''
}

function removeMediationEffect(idx) {
  mediationEffects.value.splice(idx, 1)
}

function clearMediationEffects() {
  mediationEffects.value = []
}

function miAutoRefitReason(it) {
  const guard = evaluateMiGuard({
    miItem: it,
    adoptionCount: Number(modelStore.miAdoptionCount || 0),
    currentSyntax: modelStore.lavaanSyntax,
    thresholds: { autoRefitAdoptionCap: 3 },
  })
  if (guard.allowAutoRefit) return ''
  const msg = String(guard.confirmations?.[0]?.message || '').trim()
  return msg || '门禁未通过（安全默认：仅采纳到草稿）。'
}

function miAutoRefitAllowed(it) {
  const guard = evaluateMiGuard({
    miItem: it,
    adoptionCount: Number(modelStore.miAdoptionCount || 0),
    currentSyntax: modelStore.lavaanSyntax,
    thresholds: { autoRefitAdoptionCap: 3 },
  })
  return Boolean(guard.allowAutoRefit)
}

function applyMiToSyntaxWithHint(it) {
  const reason = miAutoRefitReason(it)
  applyMiToSyntax(it)
  if (reason) {
    showToast('已采纳到草稿：请回到理论框架检查后再手动重估')
  }
}

async function runFit() {
  if (!canFit.value) return
  if (needsMissingStrategy.value) {
    pushWarningNotice(noticeStore, '缺失率 > 5%：请先在数据管理页选择缺失值处理方案。')
    return
  }
  try {
    await statsStore.fitModelAsync({
      data_key: dataStore.dataKey,
      lavaan_syntax: modelStore.lavaanSyntax,
      estimator: localEstimator.value,
      missing_strategy: localMissingStrategy.value || dataStore.missingStrategy || 'listwise',
    })
  } catch (_) {
    // 错误信息由 store 统一展示
  }
}

async function refitWithConfirm() {
  if (!canFit.value) return
  if (needsMissingStrategy.value) {
    pushWarningNotice(noticeStore, '缺失率 > 5%：请先在数据管理页选择缺失值处理方案。')
    return
  }
  const ok = await requestUserConfirm(dialogStore, {
    title: '重新估算确认',
    message: `将按当前设置重新估算：\n- estimator=${localEstimator.value}\n- missing=${localMissingStrategy.value || dataStore.missingStrategy || 'listwise'}\n\n继续？`,
    confirmText: '继续估算',
    cancelText: '取消',
  })
  if (!ok) return
  await runFit()
}

async function clearOldResultsWithConfirm() {
  const ok = await requestUserConfirm(dialogStore, {
    title: '清空旧结果确认',
    message: '将清空当前拟合度、参数表、Bootstrap 与多群组等结果展示（不影响 lavaan 语法）。继续？',
    confirmText: '确认清空',
    cancelText: '取消',
  })
  if (!ok) return
  statsStore.clearAllResults()
  showToast('已清空旧结果。建议重新运行一次估算。')
}

async function loadMi() {
  if (!dataStore.dataKey || !modelStore.lavaanSyntax) return
  if (!lavaanAvailable.value) {
    miHint.value = lavaanGateText.value || '当前环境未启用 lavaan，MI 不可用。'
    miItems.value = []
    miSupported.value = false
    return
  }
  miLoading.value = true
  miHint.value = ''
  miItems.value = []
  miSupported.value = false
  try {
    const { data } = await api.post('/api/v1/stats/mi', {
      data_key: dataStore.dataKey,
      lavaan_syntax: modelStore.lavaanSyntax,
      top_k: 15,
      mi_threshold: 3.84,
    })
    miSupported.value = Boolean(data?.supported)
    // E3-0：标准化 MI item 字段，补齐 source/raw，避免前端依赖“某列一定存在”
    const rawItems = Array.isArray(data?.items) ? data.items : []
    miItems.value = rawItems.map((it) => {
      const lhs = String(it?.lhs ?? '').trim()
      const op = String(it?.op ?? '').trim()
      const rhs = String(it?.rhs ?? '').trim()
      const mi = it?.mi ?? null
      const epc = it?.epc ?? null
      const source = String(it?.source ?? '').trim() || 'lavaan::modindices'
      return { lhs, op, rhs, mi, epc, source, raw: it && typeof it === 'object' ? it : {} }
    })
    miHint.value = data?.message || ''
    loadIgnoredMi()
  } catch (e) {
    const detail = e?.response?.data?.detail
    miHint.value =
      (typeof detail === 'string' ? detail : detail?.message) ||
      e.message ||
      'MI 请求失败'
  } finally {
    miLoading.value = false
  }
}

function applyMiToSyntax(it) {
  if (!it) return
  const beforeTag = currentSyntaxTag.value
  const notes = []
  const beforeSyntaxText = modelStore.lavaanSyntax
  const beforeModelForm = modelStore.readModelFormPersisted()
  const syncRes = modelStore.applyMiToModelFormPersisted({ lhs: it.lhs, op: it.op, rhs: it.rhs })
  if (syncRes?.ok === false) {
    showToast(syncRes.message || '同步表单失败，将仅追加语法')
    notes.push(syncRes.message || '同步表单失败')
  } else if (syncRes?.applied) {
    showToast(syncRes.message || '已同步到表单草稿')
    notes.push(syncRes.message || '已同步到表单草稿')
  }

  const res = modelStore.appendLavaanLineFromMi({ lhs: it.lhs, op: it.op, rhs: it.rhs })
  if (!res.ok) {
    pushErrorNotice(noticeStore, res.message || '未能追加语法')
    return
  }
  if (res.duplicate) {
    showToast('该条已在当前 lavaan 语法中，未重复添加')
    return
  }
  const afterTag = currentSyntaxTag.value
  const afterSyntaxText = modelStore.lavaanSyntax
  const afterModelForm = modelStore.readModelFormPersisted()

  // E3-1：记录采纳记录（按“采纳后语法版本号”分桶，便于在当前版本查看追溯）
  const appliedTo = syncRes?.applied ? 'both' : 'syntax'
  miAdoptionStore.addAdoption(
    miAdoptionStore.makeRecord({
      miItem: it,
      appliedTo,
      beforeSyntaxFingerprint: beforeTag,
      afterSyntaxFingerprint: afterTag,
      beforeSyntaxText,
      afterSyntaxText,
      beforeModelForm: syncRes?.applied ? beforeModelForm : null,
      afterModelForm: syncRes?.applied ? afterModelForm : null,
      notes: notes.filter(Boolean).join('；'),
    }),
    { bucketTag: afterTag }
  )

  // 语法发生变化：清空旧的估算/Bootstrap/不变性结果，避免“旧结果配新语法”误导
  statsStore.clearAllResults()
  // 采纳后默认将该条标记为“已忽略”（避免继续出现在候选列表里）
  ignoredMiKeys.value.add(miKey(it))
  saveIgnoredMi()
  showToast('已追加到 lavaan 语法。下一步：点击上方“重新估算”刷新拟合度与参数表。')
}

async function applyMiAndRefit(it) {
  if (!it) return
  if (!canFit.value) return
  if (needsMissingStrategy.value) {
    pushWarningNotice(noticeStore, '缺失率 > 5%：请先在数据管理页选择缺失值处理方案。')
    return
  }
  const guard = evaluateMiGuard({
    miItem: it,
    adoptionCount: Number(modelStore.miAdoptionCount || 0),
    currentSyntax: modelStore.lavaanSyntax,
    thresholds: { autoRefitAdoptionCap: 3 },
  })
  if (!guard.allowAutoRefit) {
    pushWarningNotice(noticeStore, guard.confirmations?.[0]?.message || '为避免过拟合，已默认禁用“采纳并重算”。')
    applyMiToSyntax(it)
    return
  }
  for (const step of guard.confirmations || []) {
    const ok = await requestUserConfirm(dialogStore, {
      title: 'MI 采纳确认',
      message: step.message || '继续？',
      confirmText: '继续',
      cancelText: '取消',
    })
    if (!ok) {
      if (step.defaultOnCancel === 'apply_only') {
        applyMiToSyntax(it)
      }
      return
    }
  }
  const before = modelStore.lavaanSyntax
  const line = `${String(it.lhs || '').trim()} ${String(it.op || '').trim()} ${String(it.rhs || '').trim()}`.trim()
  applyMiToSyntax(it)
  // 如果语法没变（重复/失败），就不强行重算
  if (modelStore.lavaanSyntax === before) return
  await runFit()
  if (line) {
    await copyText(line, '已重算，并复制本次采纳的语句')
  } else {
    showToast('已重算完成')
  }
}

async function copyMiLine(it) {
  if (!it) return
  const line = `${String(it.lhs || '').trim()} ${String(it.op || '').trim()} ${String(it.rhs || '').trim()}`.trim()
  if (!line) return
  await copyText(line, '已复制该条 MI（lavaan 语句）')
}

function applyMiAndGo(it) {
  applyMiToSyntax(it)
  // 无论是否重复/失败，都让用户自己判断是否需要去建模页；这里尽量只在“语法存在”时跳转
  if (dataStore.dataKey && modelStore.lavaanSyntax) {
    router.push({ path: '/model', query: { focus: 'syntax' } })
  }
}

function goModelAfterMi() {
  router.push({ path: '/model', query: { focus: 'syntax' } })
}

async function runBootstrap() {
  if (!canFit.value) return
  if (needsMissingStrategy.value) {
    pushWarningNotice(noticeStore, '缺失率 > 5%：请先在数据管理页选择缺失值处理方案。')
    return
  }
  if (!canRunBootstrap.value) {
    pushWarningNotice(noticeStore, '请先至少添加一条中介路径')
    return
  }
  try {
    const covariates = String(bootCovariatesText.value || '')
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    await statsStore.runBootstrapMediationAsync({
      data_key: dataStore.dataKey,
      lavaan_syntax: modelStore.lavaanSyntax,
      estimator: localEstimator.value,
      missing_strategy: localMissingStrategy.value || dataStore.missingStrategy || 'listwise',
      effects: mediationEffects.value.map((item) => ({
        sequence: item.sequence,
        label: item.label,
      })),
      covariates,
      n_boot: bootN.value || 2000,
      ci_level: 0.95,
      use_standardized: true,
    })
  } catch (_) {
    // 错误由 store 展示
  }
}

function copyCurrentSyntaxToB() {
  if (!canExportSyntax.value) return
  compareSyntaxB.value = String(modelStore.lavaanSyntax || '')
  showToast('已复制当前语法到 Model B（请按需修改为嵌套模型）')
}

async function runModelCompare() {
  if (!canRunModelCompare.value) {
    pushWarningNotice(noticeStore, '请先确保：已上传数据 + 生成 lavaan 语法 + 填写 Model B 语法')
    return
  }
  try {
    await statsStore.runModelCompareAsync({
      data_key: dataStore.dataKey,
      lavaan_syntax_a: String(modelStore.lavaanSyntax || ''),
      lavaan_syntax_b: String(compareSyntaxB.value || ''),
      label_a: String(compareLabelA.value || 'Model A'),
      label_b: String(compareLabelB.value || 'Model B'),
      estimator: statsStore.estimator || localEstimator.value || 'ML',
      missing_strategy: statsStore.missingStrategy || localMissingStrategy.value || 'fiml',
    })
    showToast('模型比较已完成')
  } catch (_) {
    // 错误由 store 展示
  }
}

async function runMgaStructural() {
  if (!canRunMgaStructural.value) {
    pushWarningNotice(noticeStore, '请先确保：已上传数据 + 生成 lavaan 语法 + 运行一次估算（生成 estimates）+ 选择分组变量 + 勾选至少一条结构回归路径')
    return
  }
  try {
    const paths = (mgaChosenPaths.value || []).map((x) => ({
      predictor: String(x.predictor || '').trim(),
      outcome: String(x.outcome || '').trim(),
    }))
    const first = paths[0] || {}
    await statsStore.runMgaStructuralPathCompareAsync({
      data_key: dataStore.dataKey,
      lavaan_syntax: String(modelStore.lavaanSyntax || ''),
      group_var: String(groupVar.value || ''),
      predictor: String(first.predictor || ''),
      outcome: String(first.outcome || ''),
      paths,
      estimator: statsStore.estimator || localEstimator.value || 'ML',
      missing_strategy: statsStore.missingStrategy || localMissingStrategy.value || 'fiml',
    })
    showToast('MGA 逐步比较已完成')
  } catch (_) {
    // 错误由 store 展示
  }
}

function selectAllMgaPaths() {
  mgaSelectedKeys.value = (mgaPathOptions.value || []).map((x) => x.key)
}

function clearMgaPaths() {
  mgaSelectedKeys.value = []
}

async function runInvariance() {
  if (!canFit.value) return
  if (needsMissingStrategy.value) {
    pushWarningNotice(noticeStore, '缺失率 > 5%：请先在数据管理页选择缺失值处理方案。')
    return
  }
  if (!groupVar.value) {
    pushWarningNotice(noticeStore, '请选择分组变量')
    return
  }
  try {
    await statsStore.runInvarianceConfiguralAsync({
      data_key: dataStore.dataKey,
      lavaan_syntax: modelStore.lavaanSyntax,
      estimator: localEstimator.value,
      missing_strategy: localMissingStrategy.value || dataStore.missingStrategy || 'listwise',
      group_var: groupVar.value,
      max_groups: 8,
    })
  } catch (_) {
    // 错误由 store 展示
  }
}

async function runModeration() {
  if (!canFit.value) return
  if (needsMissingStrategy.value) {
    pushWarningNotice(noticeStore, '缺失率 > 5%：请先在数据管理页选择缺失值处理方案。')
    return
  }
  if (!canRunModeration.value) {
    pushWarningNotice(noticeStore, '请先选择 X / W / Y')
    return
  }
  try {
    const covariates = String(modCovariatesText.value || '')
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    await statsStore.runModerationAnalysisAsync({
      data_key: dataStore.dataKey,
      x: modX.value,
      w: modW.value,
      y: modY.value,
      covariates,
      moderator_type: modType.value || 'continuous',
      missing_strategy: localMissingStrategy.value || dataStore.missingStrategy || 'listwise',
    })
  } catch (_) {
    // 错误由 store 展示
  }
}

async function runModeratedMediation() {
  if (!canFit.value) return
  if (needsMissingStrategy.value) {
    pushWarningNotice(noticeStore, '缺失率 > 5%：请先在数据管理页选择缺失值处理方案。')
    return
  }
  if (!canRunModeratedMediation.value) {
    pushWarningNotice(noticeStore, '请选择互不相同的 X / M / Y / W')
    return
  }
  try {
    const covariates = String(mmCovariatesText.value || '')
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    await statsStore.runModeratedMediationAsync({
      data_key: dataStore.dataKey,
      x: mmX.value,
      m: mmM.value,
      y: mmY.value,
      w: mmW.value,
      hayes_model: mmHayesModel.value || '7',
      w_type: mmWType.value || 'continuous',
      covariates,
      n_boot: Number(mmBootN.value) || 2000,
      ci_level: 0.95,
      missing_strategy: localMissingStrategy.value || dataStore.missingStrategy || 'listwise',
    })
  } catch (_) {
    // 错误由 store 展示
  }
}

async function runLatentInteractionProbe() {
  if (!canFit.value) return
  if (needsMissingStrategy.value) {
    pushWarningNotice(noticeStore, '缺失率 > 5%：请先在数据管理页选择缺失值处理方案。')
    return
  }
  if (!canRunLatentInteractionProbe.value) {
    pushWarningNotice(noticeStore, '请填写互不相同的结局 Y、F1、F2')
    return
  }
  try {
    await statsStore.runLatentInteractionProbeAsync({
      data_key: dataStore.dataKey,
      lavaan_syntax: modelStore.lavaanSyntax,
      y: liProbeY.value.trim(),
      f1: liProbeF1.value.trim(),
      f2: liProbeF2.value.trim(),
      estimator: statsStore.estimator || localEstimator.value || 'ML',
      missing_strategy: localMissingStrategy.value || dataStore.missingStrategy || 'listwise',
    })
  } catch (_) {
    // 错误由 store 展示
  }
}

async function runInvarianceSeries() {
  if (!canFit.value) return
  if (needsMissingStrategy.value) {
    pushWarningNotice(noticeStore, '缺失率 > 5%：请先在数据管理页选择缺失值处理方案。')
    return
  }
  if (!groupVar.value) {
    pushWarningNotice(noticeStore, '请选择分组变量')
    return
  }
  try {
    await statsStore.runInvarianceLavaanSeriesAsync({
      data_key: dataStore.dataKey,
      lavaan_syntax: modelStore.lavaanSyntax,
      group_var: groupVar.value,
      missing_strategy: localMissingStrategy.value || dataStore.missingStrategy || 'fiml',
    })
  } catch (_) {
    // 错误由 store 展示
  }
}

function downloadBlob(blob, filename) {
  delegateDownloadBlob({
    blob,
    filename: formatDownloadBlobFilename(filename),
    createObjectURL: (value) => URL.createObjectURL(value),
    revokeObjectURL: (value) => URL.revokeObjectURL(value),
    createAnchor: () => document.createElement('a'),
    appendToBody: (node) => document.body.appendChild(node),
  })
}

function showToast(msg) {
  delegateShowToast({
    msg,
    clearTimer: () => {
      if (toastTimer) clearTimeout(toastTimer)
    },
    setTimer: (value, duration) => {
      toastTimer = typeof value === 'function' ? setTimeout(value, duration) : value
    },
    setMessage: (value) => {
      toastMessage.value = value
    },
  })
}

async function copyText(text, okMsg) {
  try {
    await navigator.clipboard.writeText(String(text || ''))
    showToast(okMsg || '已复制')
  } catch (_) {
    pushErrorNotice(noticeStore, '复制失败，请检查剪贴板权限')
  }
}

async function exportApaXlsx() {
  if (!canExportSyntax.value) {
    pushWarningNotice(noticeStore, '请先上传数据并生成 lavaan 语法')
    return
  }
  if (!canExportApa.value) {
    pushWarningNotice(noticeStore, 'APA 导出前请先运行一次 ML 估算')
    return
  }
  if (needsMissingStrategy.value) {
    pushWarningNotice(noticeStore, '缺失率 > 5%：请先在数据管理页选择缺失值处理方案。')
    return
  }
  try {
    exportingApaXlsx.value = true
    const adoptions = miAdoptions.value || []
    const firstAt = adoptions.length ? (adoptions[adoptions.length - 1]?.applied_at || '') : ''
    const lastAt = adoptions.length ? (adoptions[0]?.applied_at || '') : ''
    const lastId = adoptions.length ? (adoptions[0]?.id || '') : ''
    const res = await api.post(
      '/api/v1/export/apa-table',
      {
        data_key: dataStore.dataKey,
        lavaan_syntax: modelStore.lavaanSyntax,
        fit_indices: statsStore.fitIndices || null,
        estimator: statsStore.estimator || localEstimator.value || null,
        missing_strategy: statsStore.missingStrategy || localMissingStrategy.value || null,
        fit_ran_at: statsStore.lastFitAt || null,
        syntax_tag: String(currentSyntaxTag.value || ''),
        last_fit_syntax_tag: String(lastFitSyntaxTag.value || ''),
        fit_stale: Boolean(isFitStale.value),
        mi_adoption_bucket_tag: String(currentSyntaxTag.value || ''),
        mi_adoption_first_at: String(firstAt || ''),
        mi_adoption_last_at: String(lastAt || ''),
        mi_adoption_last_id: String(lastId || ''),
        allow_stale_export: Boolean(allowStaleExport.value),
        mi_adoption_count: Number(miAdoptionCountForTag.value || 0),
        mi_ignored_count: Number(ignoredMiCount.value || 0),
        mi_risk_filter: String(miRiskFilter.value || 'all'),
        estimates: statsStore.estimates || [],
        bootstrap: statsStore.bootstrapResult || null,
        moderation: statsStore.moderationResult || null,
        moderated_mediation: statsStore.moderatedMediationResult || null,
        model_comparison: statsStore.modelCompareResult || null,
        mga_structural: statsStore.mgaResult || null,
        invariance: statsStore.invarianceResult || null,
        invariance_series: statsStore.invarianceSeriesResult || null,
        invariance_series_summary_lines: invSeriesSummaryLines.value || [],
        invariance_series_conclusion: invSeriesConclusion.value || null,
        invariance_series_report: {
          lite: invSeriesReportTextLite.value || '',
          strict: invSeriesReportTextStrict.value || '',
        },
        path_summary_rows: pathSummaryRows.value || [],
        path_summary_lines: pathSummaryLines.value || [],
        path_summary_report_text: pathSummaryReportText.value || '',
        integrated_paper_paragraph: integratedPaperParagraph.value || '',
        latent_interaction: statsStore.latentInteractionResult || null,
        project_name: projectName.value || 'OpenSEM',
      },
      { responseType: 'blob' }
    )
    downloadBlob(res.data, getFilenameFromHeaders(res.headers, 'OpenSEM_apa_table.xlsx'))
    showToast('已导出 APA .xlsx')
  } catch (e) {
    pushErrorNotice(noticeStore, await parseBlobError(e, 'APA 导出失败'))
  } finally {
    exportingApaXlsx.value = false
  }
}

async function exportLavaanSyntax() {
  if (!canExportSyntax.value) {
    pushWarningNotice(noticeStore, '请先上传数据并生成 lavaan 语法')
    return
  }
  if (needsMissingStrategy.value) {
    pushWarningNotice(noticeStore, '缺失率 > 5%：请先在数据管理页选择缺失值处理方案。')
    return
  }
  try {
    exportingSyntax.value = true
    const res = await api.post(
      '/api/v1/export/lavaan-syntax',
      {
        data_key: dataStore.dataKey,
        lavaan_syntax: modelStore.lavaanSyntax,
        project_name: projectName.value || 'OpenSEM',
      },
      { responseType: 'blob' }
    )
    downloadBlob(res.data, getFilenameFromHeaders(res.headers, 'OpenSEM_model.lavaan.txt'))
    showToast('已导出 lavaan 语法')
  } catch (e) {
    pushErrorNotice(noticeStore, await parseBlobError(e, 'lavaan 导出失败'))
  } finally {
    exportingSyntax.value = false
  }
}

async function exportApaDocx() {
  if (!canExportSyntax.value) {
    pushWarningNotice(noticeStore, '请先上传数据并生成 lavaan 语法')
    return
  }
  if (!canExportApa.value) {
    pushWarningNotice(noticeStore, 'APA 导出前请先运行一次 ML 估算')
    return
  }
  if (needsMissingStrategy.value) {
    pushWarningNotice(noticeStore, '缺失率 > 5%：请先在数据管理页选择缺失值处理方案。')
    return
  }
  try {
    exportingApaDocx.value = true
    const adoptions = miAdoptions.value || []
    const firstAt = adoptions.length ? (adoptions[adoptions.length - 1]?.applied_at || '') : ''
    const lastAt = adoptions.length ? (adoptions[0]?.applied_at || '') : ''
    const lastId = adoptions.length ? (adoptions[0]?.id || '') : ''
    const res = await api.post(
      '/api/v1/export/apa-table-docx',
      {
        data_key: dataStore.dataKey,
        lavaan_syntax: modelStore.lavaanSyntax,
        fit_indices: statsStore.fitIndices || null,
        estimator: statsStore.estimator || localEstimator.value || null,
        missing_strategy: statsStore.missingStrategy || localMissingStrategy.value || null,
        fit_ran_at: statsStore.lastFitAt || null,
        syntax_tag: String(currentSyntaxTag.value || ''),
        last_fit_syntax_tag: String(lastFitSyntaxTag.value || ''),
        fit_stale: Boolean(isFitStale.value),
        mi_adoption_bucket_tag: String(currentSyntaxTag.value || ''),
        mi_adoption_first_at: String(firstAt || ''),
        mi_adoption_last_at: String(lastAt || ''),
        mi_adoption_last_id: String(lastId || ''),
        allow_stale_export: Boolean(allowStaleExport.value),
        mi_adoption_count: Number(miAdoptionCountForTag.value || 0),
        mi_ignored_count: Number(ignoredMiCount.value || 0),
        mi_risk_filter: String(miRiskFilter.value || 'all'),
        estimates: statsStore.estimates || [],
        bootstrap: statsStore.bootstrapResult || null,
        moderation: statsStore.moderationResult || null,
        moderated_mediation: statsStore.moderatedMediationResult || null,
        model_comparison: statsStore.modelCompareResult || null,
        mga_structural: statsStore.mgaResult || null,
        invariance: statsStore.invarianceResult || null,
        invariance_series: statsStore.invarianceSeriesResult || null,
        invariance_series_summary_lines: invSeriesSummaryLines.value || [],
        invariance_series_conclusion: invSeriesConclusion.value || null,
        invariance_series_report: {
          lite: invSeriesReportTextLite.value || '',
          strict: invSeriesReportTextStrict.value || '',
        },
        path_summary_rows: pathSummaryRows.value || [],
        path_summary_lines: pathSummaryLines.value || [],
        path_summary_report_text: pathSummaryReportText.value || '',
        integrated_paper_paragraph: integratedPaperParagraph.value || '',
        latent_interaction: statsStore.latentInteractionResult || null,
        project_name: projectName.value || 'OpenSEM',
      },
      { responseType: 'blob' }
    )
    downloadBlob(res.data, getFilenameFromHeaders(res.headers, 'OpenSEM_apa_table.docx'))
    showToast('已导出 APA .docx')
  } catch (e) {
    pushErrorNotice(noticeStore, await parseBlobError(e, 'APA docx 导出失败'))
  } finally {
    exportingApaDocx.value = false
  }
}

onMounted(() => {
  document.querySelector('.results-view')?.classList.add('visible')
  runtimeStore.loadPersisted()
  runtimeStore.refreshHealth().catch(() => {})
  // 预加载当前语法版本的 MI 采纳记录
  miAdoptionStore.loadTag(currentSyntaxTag.value)
  try {
    const saved = localStorage.getItem(PROJECT_NAME_KEY)
    if (saved) projectName.value = saved
  } catch (_) {
    // ignore localStorage read errors
  }
  dataStore.validatePersistedDataKey().then((res) => {
    if (res?.valid === false) {
      pushWarningNotice(noticeStore, '检测到数据会话已过期，请先重新上传数据。', '会话失效')
    }
  })
})

watch(allowStaleExport, async (v) => {
  if (!v) return
  const ok = await requestUserConfirm(dialogStore, {
    title: 'STALE 导出风险确认',
    message:
      '你正在启用“允许导出过期结果（STALE）”。\n\n这可能导致导出内容与当前语法不一致、从而误导报告与审稿。\n\n建议：先点击上方“重新估算”刷新结果后再导出。\n\n仍要继续启用并允许导出吗？',
    confirmText: '继续启用',
    cancelText: '取消',
  })
  if (!ok) allowStaleExport.value = false
})

// keep project name across refreshes for repeated exports
watch(projectName, (v) => {
  try {
    localStorage.setItem(PROJECT_NAME_KEY, (v || '').trim() || 'OpenSEM')
  } catch (_) {
    // ignore localStorage write errors
  }
})

// 语法版本变化时，重新加载该版本对应的“忽略列表”
watch(currentSyntaxTag, () => {
  loadIgnoredMi()
  miAdoptionStore.loadTag(currentSyntaxTag.value)
})

async function undoMiAdoption(rec) {
  if (!rec || rec.undone_at) return
  const beforeText = String(rec.before_syntax_text ?? '')
  const afterText = String(rec.after_syntax_text ?? '')
  const beforeForm = rec.before_model_form
  const afterForm = rec.after_model_form
  const bucketTag = String(rec.after_syntax_fingerprint || '').trim() || currentSyntaxTag.value

  if (!beforeText) {
    pushErrorNotice(noticeStore, '该条采纳记录缺少 before_syntax_text（旧版本记录），无法做确定性撤销。')
    return
  }

  const currentTextNorm = normalizeSyntaxForCompare(modelStore.lavaanSyntax)
  const expectedAfterNorm = normalizeSyntaxForCompare(afterText)

  let msg =
    '将撤销该条 MI 采纳：\n- 语法会回滚到采纳前版本\n- 这会清空旧的拟合/Bootstrap/不变性结果（避免误导）\n\n继续？'
  const shouldRollbackForm = String(rec.applied_to || '').trim() === 'both'
  if (shouldRollbackForm) {
    if (!beforeForm) {
      msg =
        '该条记录显示曾同步到建模表单，但缺少 before_model_form 快照。\n\n为避免不一致，本次只能回滚语法；建模表单不会自动回滚。\n\n仍要继续吗？'
    } else {
      msg =
        '将撤销该条 MI 采纳：\n- 语法会回滚到采纳前版本\n- 建模表单草稿也会回滚到采纳前版本（保持一致）\n- 这会清空旧的拟合/Bootstrap/不变性结果（避免误导）\n\n继续？'
    }
  }
  if (afterText && expectedAfterNorm && currentTextNorm !== expectedAfterNorm) {
    msg =
      '检测到当前语法已与该条采纳记录的“采纳后语法”不一致。\n\n为保证确定性撤销，将直接回滚到该记录的 before 版本，这会覆盖你当前的语法内容。\n\n仍要继续撤销吗？'
  }
  const ok = await requestUserConfirm(dialogStore, {
    title: '撤销 MI 采纳确认',
    message: msg,
    confirmText: '继续撤销',
    cancelText: '取消',
  })
  if (!ok) return

  // 确定性回滚：直接恢复快照
  modelStore.setLavaanSyntax(beforeText)
  if (shouldRollbackForm && beforeForm) {
    const formOk = modelStore.writeModelFormPersisted(beforeForm)
    if (!formOk) {
      showToast('语法已回滚，但表单草稿回滚失败（localStorage 不可用）')
    }
  }
  statsStore.clearAllResults()
  modelStore.decrementMiAdoptionCount()

  // 标记该条记录已撤销（在其原 bucket 中更新）
  miAdoptionStore.updateRecordInTag(bucketTag, rec.id, {
    undone_at: new Date().toISOString(),
    undone_reason: 'user_undo',
  })

  showToast('已撤销该条采纳（语法已回滚）。建议重新估算以刷新结果。')
}
</script>

<style scoped>
.results-view {
  --osem-core-bg-nebula-a: rgba(97, 164, 245, 0.18);
  --osem-core-bg-nebula-b: rgba(248, 168, 115, 0.1);
  --osem-core-bg-nebula-c: rgba(113, 146, 234, 0.17);
  padding: clamp(1.5rem, 3vw, 2.5rem);
}

.view-layout {
  display: grid;
  grid-template-columns: 1fr 260px;
  gap: clamp(1.5rem, 3vw, 2rem);
  align-items: start;
}

.section-label, .sidebar-label {
  margin-bottom: 0.5rem;
}

.section-rule {
  height: 1px;
  background: var(--line-soft);
  margin-bottom: 1rem;
}

.fit-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
  flex-wrap: wrap;
}

.used-n {
  font-size: 0.85rem;
  color: var(--text-muted);
}

.fit-item {
  flex: 1;
  min-width: 80px;
  padding: 1rem;
  background: var(--surface-elevated);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-sm);
  text-align: center;
}

.fit-value {
  display: block;
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
}

.fit-label {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.export-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.project-name-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.75rem;
  flex-wrap: wrap;
}

.project-name-input {
  min-width: 220px;
  max-width: 360px;
}

.export-hint {
  margin-top: 0.5rem;
  font-size: 0.84rem;
  color: var(--text-muted);
  line-height: 1.6;
}

.export-stale-toggle {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  margin-top: 0.5rem;
  padding: 0.55rem 0.65rem;
  border: 1px dashed rgba(144, 186, 252, 0.45);
  border-radius: var(--radius-sm);
  background: rgba(16, 29, 50, 0.72);
}

.export-stale-toggle input {
  margin-top: 0.15rem;
}

.export-stale-toggle span {
  color: var(--text-secondary);
  line-height: 1.35;
}

.export-success {
  margin-top: 0.45rem;
  font-size: 0.84rem;
  color: var(--success);
}

.btn-icon { font-size: 1.1em; }

.interpret-box {
  padding: 1rem;
  background: transparent;
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-sm);
}

.interpret-box p {
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin-bottom: 0.35rem;
}

.sidebar-tip {
  font-size: 0.85rem;
  color: var(--text-muted);
  line-height: 1.62;
}

.fit-error {
  color: #ffc0ca;
  margin-bottom: 0.6rem;
  font-size: 0.88rem;
}

.fit-error-hint {
  margin: -0.35rem 0 0.6rem;
  font-size: 0.84rem;
  color: var(--text-muted);
}

.bootstrap-feedback {
  margin: 0.55rem 0 0.75rem;
}

.model-compare-feedback {
  margin: 0.55rem 0 0.75rem;
}

.fit-stale {
  margin: 0 0 0.75rem;
  padding: 0.65rem 0.75rem;
  border: 1px solid rgba(243, 178, 95, 0.52);
  background: rgba(243, 178, 95, 0.14);
  color: #f7d29d;
  border-radius: var(--radius-sm);
  font-size: 0.86rem;
}

.fit-stale-meta {
  display: block;
  margin-top: 0.35rem;
  font-size: 0.82rem;
  color: rgba(247, 210, 157, 0.88);
}

.status-text {
  margin-top: 0.75rem;
  font-size: 0.9rem;
}

.status-good { color: #84e2b4; }
.status-borderline { color: #f0c987; }
.status-poor { color: var(--error); }

.status-hint {
  margin-top: 1.5rem;
  font-size: 0.85rem;
  color: var(--text-muted);
}

.mi-list {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  margin-bottom: 0.65rem;
}

.mi-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin: 0.45rem 0 0.55rem;
}

.mi-count {
  font-size: 0.76rem;
  color: var(--text-muted);
}

.mi-item {
  padding: 0.55rem 0.6rem;
  background: rgba(12, 22, 40, 0.86);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-sm);
}

.mi-item-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.mi-formula {
  font-family: 'Courier New', monospace;
  font-size: 0.78rem;
  word-break: break-all;
  color: var(--text-primary);
}

.mi-meta {
  font-size: 0.72rem;
  color: var(--text-muted);
  margin: 0.3rem 0 0.45rem;
}

.mi-tags {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
  margin-bottom: 0.45rem;
}

.mi-tag {
  font-size: 0.68rem;
  line-height: 1;
  padding: 0.2rem 0.35rem;
  border: 1px solid var(--line-soft);
  background: rgba(255, 255, 255, 0.02);
  color: var(--text-secondary);
}

.mi-tag-kind {
  border-color: rgba(143, 202, 255, 0.44);
  background: rgba(143, 202, 255, 0.12);
  color: #d5ecff;
}

.mi-tag-risk-low {
  border-color: rgba(57, 197, 136, 0.52);
  background: rgba(57, 197, 136, 0.14);
  color: #baf5d9;
}

.mi-tag-risk-medium {
  border-color: rgba(243, 178, 95, 0.52);
  background: rgba(243, 178, 95, 0.14);
  color: #f7d29d;
}

.mi-tag-risk-high {
  border-color: rgba(240, 122, 134, 0.56);
  background: rgba(240, 122, 134, 0.14);
  color: #ffd4db;
}

.mi-text {
  font-size: 0.78rem;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
}

.mi-warning {
  margin: 0.55rem 0 0.75rem;
  padding: 0.55rem 0.6rem;
  border: 1px solid rgba(243, 178, 95, 0.52);
  background: rgba(243, 178, 95, 0.14);
  color: #f7d29d;
  border-radius: var(--radius-sm);
  font-size: 0.84rem;
}

.mi-ignore-btn {
  border-color: rgba(243, 178, 95, 0.48);
  background: rgba(243, 178, 95, 0.12);
  color: #f7d29d;
}

.mi-ignore-btn:hover {
  border-color: rgba(243, 178, 95, 0.72);
  color: #ffe3bd;
}

.mi-apply-btn {
  display: inline-block;
  padding: 0.28rem 0.5rem;
  font-size: 0.72rem;
  border: 1px solid var(--line-soft);
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 8px;
}

.mi-apply-btn:hover {
  border-color: var(--line-strong);
  color: #d8edff;
}

.mi-apply-cta {
  border-color: rgba(57, 197, 136, 0.52);
  background: rgba(57, 197, 136, 0.14);
  color: #baf5d9;
}

.mi-apply-cta:hover {
  border-color: rgba(57, 197, 136, 0.74);
  color: #d8ffeb;
}

.mi-copy-btn {
  display: inline-block;
  padding: 0.28rem 0.5rem;
  font-size: 0.72rem;
  border: 1px solid var(--line-soft);
  background: rgba(255, 255, 255, 0.02);
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 8px;
}

.mi-copy-btn:hover {
  border-color: var(--line-strong);
  color: #d8edff;
}

.mi-apply-link {
  padding: 0;
  border: none;
  background: none;
  font-size: 0.78rem;
  color: var(--accent);
  text-decoration: underline;
  cursor: pointer;
  text-align: left;
}

.mi-apply-link-block {
  margin-top: 0.15rem;
}

.mi-btn { margin-top: 0.5rem; }

.mi-adoptions {
  margin-top: 0.6rem;
  border: 1px solid var(--line-soft);
  border-radius: 12px;
  background: rgba(11, 20, 37, 0.74);
  padding: 0.6rem;
}

.mi-adopt-item {
  padding: 0.55rem 0.55rem 0.5rem;
  border: 1px solid var(--line-soft);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  margin-bottom: 0.5rem;
}

.mi-adopt-item:last-child {
  margin-bottom: 0;
}

.inv-cards {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.75rem;
  margin-top: 0.85rem;
}

.inv-card {
  border: 1px solid var(--line-soft);
  background: rgba(11, 20, 37, 0.8);
  border-radius: 12px;
  padding: 0.85rem 0.85rem 0.8rem;
}

.inv-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.55rem;
}

.inv-card-title {
  font-weight: 700;
  color: var(--text-primary);
  font-size: 0.9rem;
}

.inv-card-badge {
  font-family: var(--font-ui);
  font-weight: 800;
  letter-spacing: 0.08em;
  font-size: 0.7rem;
  padding: 0.28rem 0.5rem;
  border-radius: 999px;
  border: 1px solid var(--line-soft);
  text-transform: uppercase;
}

.inv-badge-pass { background: rgba(57, 197, 136, 0.14); color: #baf5d9; border-color: rgba(57, 197, 136, 0.5); }
.inv-badge-fail { background: rgba(240, 122, 134, 0.14); color: #ffd4db; border-color: rgba(240, 122, 134, 0.56); }
.inv-badge-unknown { background: rgba(159, 178, 213, 0.14); color: #cfdef7; border-color: rgba(159, 178, 213, 0.46); }

.inv-card-body {
  display: grid;
  gap: 0.35rem;
}

.inv-card-row {
  display: grid;
  grid-template-columns: 92px 1fr;
  gap: 0.75rem;
  align-items: baseline;
}

.inv-card-k {
  color: var(--text-muted);
  font-size: 0.78rem;
}

.inv-card-v {
  color: var(--text-primary);
  font-size: 0.82rem;
  line-height: 1.35;
}

.inv-report {
  margin-top: 0.9rem;
  border: 1px solid var(--line-soft);
  border-radius: 12px;
  overflow: hidden;
  background: var(--panel);
}

.inv-report-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.65rem 0.75rem;
  border-bottom: 1px solid var(--line-soft);
}

.inv-report-title {
  font-weight: 700;
  color: var(--text-primary);
  font-size: 0.9rem;
}

.inv-report-copy {
  padding: 0.45rem 0.65rem;
}

.inv-report-pre {
  margin: 0;
  padding: 0.75rem;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 0.78rem;
  color: var(--text-primary);
  background: transparent;
}

.inv-model-cards {
  margin-top: 0.75rem;
}

.sidebar {
  display: grid;
  gap: 0.8rem;
}

.sidebar-section {
  padding: 0.85rem 0.9rem;
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-md);
  background: rgba(11, 20, 37, 0.82);
  box-shadow: var(--shadow-sm);
}

.config-item {
  min-width: 11rem;
}

@media (max-width: 1023.98px) {
  .fit-item {
    min-width: 140px;
  }

  .config-item {
    min-width: 9.5rem;
  }
}

@media (max-width: 768px) {
  .view-layout { grid-template-columns: 1fr; }
  .results-view {
    padding: var(--osem-core-outer-pad, clamp(0.9rem, 4vw, 1.25rem));
  }
  .fit-preview {
    gap: 0.6rem;
  }
  .fit-item {
    min-width: calc(50% - 0.35rem);
    padding: 0.72rem;
  }
  .action-row {
    gap: 0.5rem;
  }
  .action-row :is(button, .osem-btn) {
    width: 100%;
  }
  .project-name-input {
    min-width: 0;
    width: 100%;
    max-width: none;
  }
  .sidebar-section {
    padding: 0.72rem 0.75rem;
  }
}

@media (max-width: 420px) {
  .fit-item {
    min-width: 100%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .fit-item,
  .mi-apply-btn,
  .mi-copy-btn {
    transition: none !important;
  }
}
</style>
