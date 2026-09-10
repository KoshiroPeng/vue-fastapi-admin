<template>
  <AppPage :show-footer="false">
    <section class="statistics-page">
      <header class="dashboard-header">
        <div>
          <p class="eyebrow">SZX · NETWORK PULSE</p>
          <h1>认证统计</h1>
          <p>NCE 实时聚合视图 · 统计结果短时缓存，不保存旅客认证明细。</p>
        </div>
        <div class="header-actions">
          <n-date-picker
            v-model:value="selectedDate"
            type="date"
            :is-date-disabled="disableFutureDate"
          />
          <n-button type="primary" :loading="loading" @click="loadStatistics">
            <template #icon><TheIcon icon="ph:arrows-clockwise-bold" /></template>
            刷新看板
          </n-button>
        </div>
      </header>

      <n-alert v-if="errorMessage" type="error" class="mb-16">{{ errorMessage }}</n-alert>

      <n-spin :show="loading && !hasData">
        <div class="kpi-grid">
          <article>
            <span class="kpi-icon blue"><TheIcon icon="ph:identification-badge-bold" /></span>
            <div>
              <small>认证请求</small><strong>{{ statistics.total_authentications || 0 }}</strong
              ><em>AUTH REQUESTS</em>
            </div>
          </article>
          <article>
            <span class="kpi-icon green"><TheIcon icon="ph:check-circle-bold" /></span>
            <div>
              <small>认证成功率</small><strong>{{ statistics.success_rate || 0 }}<i>%</i></strong
              ><em>{{ statistics.success_count || 0 }} SUCCESS</em>
            </div>
          </article>
          <article>
            <span class="kpi-icon red"><TheIcon icon="ph:x-circle-bold" /></span>
            <div>
              <small>认证失败</small><strong>{{ statistics.failure_count || 0 }}</strong
              ><em>FAILED ATTEMPTS</em>
            </div>
          </article>
          <article>
            <span class="kpi-icon cyan"><TheIcon icon="ph:wifi-high-bold" /></span>
            <div>
              <small>实时在线</small><strong>{{ statistics.online_users || 0 }}</strong
              ><em>ACTIVE CLIENTS</em>
            </div>
          </article>
        </div>

        <div class="dashboard-grid">
          <article class="trend-panel panel">
            <div class="panel-title">
              <div>
                <small>24H TRAFFIC</small>
                <h2>分时认证趋势</h2>
              </div>
              <div class="chart-legend">
                <span class="success-line">成功</span><span class="failure-line">失败</span>
              </div>
            </div>
            <div class="trend-chart">
              <svg
                viewBox="0 0 720 230"
                preserveAspectRatio="none"
                role="img"
                aria-label="24小时认证趋势"
              >
                <g class="grid-lines">
                  <line v-for="y in [30, 80, 130, 180]" :key="y" x1="35" :y1="y" x2="705" :y2="y" />
                </g>
                <polyline class="success-path" :points="successPoints" />
                <polyline class="failure-path" :points="failurePoints" />
                <g v-for="point in chartPoints" :key="point.hour">
                  <circle :cx="point.x" :cy="point.successY" r="3" class="success-dot" />
                  <circle :cx="point.x" :cy="point.failureY" r="3" class="failure-dot" />
                  <text v-if="point.hour % 3 === 0" :x="point.x" y="218" text-anchor="middle">
                    {{ point.hour }}:00
                  </text>
                </g>
              </svg>
            </div>
            <p v-if="statistics.average_auth_duration_ms === null" class="data-note">
              当前 NCE 日志契约未提供认证耗时，因此不展示推测值。
            </p>
          </article>

          <article class="panel method-panel">
            <div class="panel-title">
              <div>
                <small>CHANNEL MIX</small>
                <h2>认证方式分布</h2>
              </div>
            </div>
            <div class="method-bars">
              <div v-for="method in methodRows" :key="method.key">
                <div class="bar-label">
                  <span>{{ method.label }}</span
                  ><strong>{{ method.value }}</strong>
                </div>
                <div class="bar-track">
                  <i :style="{ width: `${method.percent}%`, background: method.color }"></i>
                </div>
                <small>{{ method.percent.toFixed(1) }}%</small>
              </div>
            </div>
          </article>

          <article class="panel failure-panel">
            <div class="panel-title">
              <div>
                <small>FAILURE DIAGNOSIS</small>
                <h2>失败原因分布</h2>
              </div>
            </div>
            <div v-if="failureRows.length" class="failure-list">
              <div v-for="item in failureRows" :key="item.code">
                <span class="reason-code">{{ item.code }}</span>
                <div>
                  <strong>{{ item.label }}</strong>
                  <div class="failure-track"><i :style="{ width: `${item.percent}%` }"></i></div>
                </div>
                <b>{{ item.value }}</b>
              </div>
            </div>
            <n-empty v-else description="当前日期暂无认证失败记录" />
          </article>

          <article class="panel source-panel">
            <div class="source-mark"><TheIcon icon="ph:database-bold" /></div>
            <div>
              <small>DATA GOVERNANCE</small>
              <h2>零业务明细持久化</h2>
              <p>统计来自 NCE RADIUS 日志和在线用户实时代理，仅将聚合结果短时写入 Redis。</p>
            </div>
            <dl>
              <div>
                <dt>统计日期</dt>
                <dd>{{ statistics.date || '—' }}</dd>
              </div>
              <div>
                <dt>缓存时长</dt>
                <dd>30 秒</dd>
              </div>
            </dl>
          </article>
        </div>
      </n-spin>
    </section>
  </AppPage>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import dayjs from 'dayjs'

import api from '@/api'
import TheIcon from '@/components/icon/TheIcon.vue'

const selectedDate = ref(dayjs().startOf('day').valueOf())
const statistics = ref({})
const loading = ref(false)
const errorMessage = ref('')
const hasData = computed(() => Boolean(statistics.value.date))

const methodDefinitions = [
  { key: 'sms', label: '短信认证', color: '#168957' },
  { key: 'wechat', label: '微信认证', color: '#1683b7' },
  { key: 'boarding_pass', label: '登机牌认证', color: '#5b6ee1' },
  { key: 'passport', label: '护照认证', color: '#d58a00' },
  { key: 'kiosk', label: '取号机认证', color: '#8a5bb8' },
  { key: 'guest', label: '其他访客', color: '#7b8c99' },
]
const failureLabels = {
  101: '密码错误',
  105: '账号锁定',
  106: '账号过期',
  111: 'MAC 不匹配',
  116: '认证超时',
  642: '验证码错误',
}

const methodRows = computed(() => {
  const total = statistics.value.total_authentications || 0
  return methodDefinitions.map((item) => {
    const value = statistics.value.method_distribution?.[item.key] || 0
    return { ...item, value, percent: total ? (value * 100) / total : 0 }
  })
})

const failureRows = computed(() => {
  const entries = Object.entries(statistics.value.failure_reasons || {}).sort((a, b) => b[1] - a[1])
  const max = Math.max(...entries.map(([, value]) => value), 1)
  return entries.map(([code, value]) => ({
    code,
    value,
    label: failureLabels[code] || '其他失败原因',
    percent: (value * 100) / max,
  }))
})

const chartPoints = computed(() => {
  const trend = statistics.value.hourly_trend || []
  const max = Math.max(...trend.flatMap((item) => [item.success, item.failure]), 1)
  return trend.map((item, index) => ({
    ...item,
    x: 40 + index * (660 / 23),
    successY: 190 - (item.success / max) * 150,
    failureY: 190 - (item.failure / max) * 150,
  }))
})
const successPoints = computed(() =>
  chartPoints.value.map((point) => `${point.x},${point.successY}`).join(' ')
)
const failurePoints = computed(() =>
  chartPoints.value.map((point) => `${point.x},${point.failureY}`).join(' ')
)

function disableFutureDate(timestamp) {
  return timestamp > dayjs().endOf('day').valueOf()
}

async function loadStatistics() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await api.getWifiStatistics({
      date: dayjs(selectedDate.value).format('YYYY-MM-DD'),
    })
    statistics.value = response.data || {}
  } catch (error) {
    errorMessage.value = error?.message || '认证统计加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadStatistics)
</script>

<style scoped>
.statistics-page {
  min-height: 100%;
  padding: 24px;
  border-radius: 14px;
  background: #f2f6f9;
}
.dashboard-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
}
.eyebrow,
.panel-title small,
.source-panel small {
  margin: 0 0 5px;
  color: #1976a8;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
}
.dashboard-header h1 {
  margin: 0;
  color: #102f47;
  font-size: 29px;
}
.dashboard-header p {
  margin: 7px 0 0;
  color: #738999;
  font-size: 13px;
}
.header-actions {
  display: flex;
  gap: 10px;
}
.header-actions .n-date-picker {
  width: 150px;
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.kpi-grid article {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 18px;
  border: 1px solid #d7e2e9;
  border-radius: 9px;
  background: #fff;
  box-shadow: 0 6px 18px rgb(31 63 84 / 5%);
}
.kpi-icon {
  display: grid;
  width: 46px;
  height: 46px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 8px;
  font-size: 23px;
}
.kpi-icon.blue {
  background: #eaf3ff;
  color: #1677ff;
}
.kpi-icon.green {
  background: #e8f8ef;
  color: #168957;
}
.kpi-icon.red {
  background: #fff0f0;
  color: #d13b43;
}
.kpi-icon.cyan {
  background: #e7f7fb;
  color: #1587a8;
}
.kpi-grid small,
.kpi-grid strong,
.kpi-grid em {
  display: block;
}
.kpi-grid small {
  color: #718797;
  font-size: 11px;
}
.kpi-grid strong {
  margin: 3px 0;
  color: #123b56;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 25px;
}
.kpi-grid strong i {
  font-size: 12px;
  font-style: normal;
}
.kpi-grid em {
  color: #9aabb6;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 8px;
  font-style: normal;
  letter-spacing: 0.08em;
}
.dashboard-grid {
  display: grid;
  grid-template-columns: 1.45fr 0.75fr;
  gap: 14px;
  margin-top: 14px;
}
.panel {
  padding: 20px;
  border: 1px solid #d7e2e9;
  border-radius: 9px;
  background: #fff;
  box-shadow: 0 6px 18px rgb(31 63 84 / 5%);
}
.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.panel-title small {
  display: block;
  margin: 0;
}
.panel-title h2,
.source-panel h2 {
  margin: 2px 0 0;
  color: #183b54;
  font-size: 16px;
}
.chart-legend {
  display: flex;
  gap: 16px;
  color: #718796;
  font-size: 10px;
}
.chart-legend span::before {
  display: inline-block;
  width: 16px;
  height: 3px;
  margin-right: 5px;
  vertical-align: middle;
  content: '';
}
.success-line::before {
  background: #168957;
}
.failure-line::before {
  background: #d13b43;
}
.trend-chart {
  height: 230px;
}
.trend-chart svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}
.grid-lines line {
  stroke: #e7edf1;
  stroke-width: 1;
}
.success-path,
.failure-path {
  fill: none;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.success-path {
  stroke: #168957;
}
.failure-path {
  stroke: #d13b43;
}
.success-dot {
  fill: #168957;
}
.failure-dot {
  fill: #d13b43;
}
.trend-chart text {
  fill: #8a9ba7;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 8px;
}
.data-note {
  margin: 8px 0 0;
  padding: 8px 10px;
  border-left: 3px solid #d49a22;
  background: #fff9ec;
  color: #8a6a27;
  font-size: 10px;
}
.method-bars {
  display: grid;
  gap: 13px;
}
.bar-label {
  display: flex;
  justify-content: space-between;
  color: #4e687b;
  font-size: 11px;
}
.bar-label strong {
  color: #183b54;
  font-family: 'Cascadia Code', Consolas, monospace;
}
.bar-track,
.failure-track {
  overflow: hidden;
  height: 6px;
  margin-top: 5px;
  border-radius: 6px;
  background: #e9eef2;
}
.bar-track i,
.failure-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
}
.method-bars small {
  color: #91a0aa;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 8px;
}
.failure-list {
  display: grid;
  gap: 11px;
}
.failure-list > div {
  display: grid;
  grid-template-columns: 42px 1fr 25px;
  align-items: center;
  gap: 10px;
}
.reason-code {
  padding: 4px;
  border-radius: 4px;
  background: #fff0f0;
  color: #c9363e;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 10px;
  text-align: center;
}
.failure-list strong {
  color: #536c7d;
  font-size: 11px;
}
.failure-list b {
  color: #c9363e;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 13px;
  text-align: right;
}
.failure-track i {
  background: #d9575d;
}
.source-panel {
  display: grid;
  grid-template-columns: 48px 1fr auto;
  align-items: center;
  gap: 14px;
}
.source-mark {
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
  border-radius: 8px;
  background: #e9f4f8;
  color: #197da2;
  font-size: 23px;
}
.source-panel p {
  margin: 5px 0 0;
  color: #788d9c;
  font-size: 10px;
}
.source-panel dl {
  display: flex;
  gap: 16px;
  margin: 0;
}
.source-panel dt {
  color: #94a3ad;
  font-size: 9px;
}
.source-panel dd {
  margin: 4px 0 0;
  color: #244a63;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 11px;
}
@media (max-width: 1050px) {
  .kpi-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 650px) {
  .statistics-page {
    padding: 14px;
  }
  .dashboard-header,
  .header-actions,
  .source-panel {
    align-items: flex-start;
    flex-direction: column;
  }
  .header-actions,
  .header-actions .n-date-picker,
  .header-actions .n-button {
    width: 100%;
  }
  .kpi-grid {
    grid-template-columns: 1fr;
  }
  .source-panel {
    display: flex;
  }
  .source-panel dl {
    width: 100%;
  }
}
</style>
