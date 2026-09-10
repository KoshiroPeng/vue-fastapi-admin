<template>
  <AppPage :show-footer="false">
    <section class="logs-page">
      <header class="page-header">
        <div>
          <p class="eyebrow">SZX · ACCESS TRACE</p>
          <h1>RADIUS 准入日志</h1>
          <p>数据实时代理自 NCE，列表中的账号、IP 和终端 MAC 已在服务端脱敏。</p>
        </div>
        <div class="header-status">
          <span class="pulse"></span>
          MOCK DATA SOURCE
        </div>
      </header>

      <n-card :bordered="false" class="filter-card">
        <div class="filter-grid">
          <label class="wide-field">
            <span>查询时间</span>
            <n-date-picker
              v-model:value="filters.dateRange"
              type="datetimerange"
              :clearable="false"
              :is-date-disabled="disableFutureDate"
            />
          </label>
          <label>
            <span>认证结果</span>
            <n-select v-model:value="filters.auth_result" :options="resultOptions" />
          </label>
          <label>
            <span>用户类型</span>
            <n-select v-model:value="filters.user_type_code" clearable :options="userTypeOptions" />
          </label>
          <label>
            <span>失败原因</span>
            <n-select
              v-model:value="filters.fail_reason_code"
              clearable
              :options="failureOptions"
            />
          </label>
          <label>
            <span>用户账号</span>
            <n-input v-model:value="filters.user_name" clearable placeholder="精确或模糊查询" />
          </label>
          <label>
            <span>终端 IP</span>
            <n-input v-model:value="filters.terminal_ip" clearable placeholder="例如 10.85.73.8" />
          </label>
          <label>
            <span>终端 MAC</span>
            <n-input
              v-model:value="filters.terminal_mac"
              clearable
              placeholder="AA-BB-CC-DD-EE-FF"
            />
          </label>
        </div>
        <div class="filter-actions">
          <p>单次查询范围最多 7 天；敏感筛选条件不会以明文写入审计日志或缓存键。</p>
          <n-space>
            <n-button @click="resetFilters">重置</n-button>
            <n-button type="primary" :loading="loading" @click="fetchLogs(true)">
              <template #icon><TheIcon icon="ph:magnifying-glass-bold" /></template>
              查询日志
            </n-button>
          </n-space>
        </div>
      </n-card>

      <n-alert v-if="errorMessage" type="error" class="mt-16">{{ errorMessage }}</n-alert>

      <div class="metric-strip">
        <div>
          <span>当前页记录</span><strong>{{ rows.length }}</strong>
        </div>
        <div>
          <span>认证成功</span><strong class="success">{{ successCount }}</strong>
        </div>
        <div>
          <span>认证失败</span><strong class="danger">{{ failureCount }}</strong>
        </div>
        <div>
          <span>游标页码</span><strong>{{ pageIndex + 1 }}</strong>
        </div>
      </div>

      <n-card :bordered="false" class="table-card">
        <n-data-table
          remote
          :columns="columns"
          :data="rows"
          :loading="loading"
          :row-key="(row) => row.id"
          :scroll-x="1320"
          :single-line="false"
          striped
        />
        <footer class="cursor-footer">
          <div>
            <span>每页</span>
            <n-select
              v-model:value="pageSize"
              size="small"
              :options="pageSizeOptions"
              @update:value="fetchLogs(true)"
            />
            <span>条</span>
          </div>
          <n-space>
            <n-button size="small" :disabled="pageIndex === 0 || loading" @click="goPrevious">
              上一页
            </n-button>
            <n-button
              size="small"
              type="primary"
              :disabled="!nextCursor || loading"
              @click="goNext"
            >
              下一页
            </n-button>
          </n-space>
        </footer>
      </n-card>
    </section>
  </AppPage>
</template>

<script setup>
import { computed, h, onMounted, reactive, ref } from 'vue'
import dayjs from 'dayjs'
import { NTag } from 'naive-ui'

import api from '@/api'
import TheIcon from '@/components/icon/TheIcon.vue'

const now = dayjs()
const initialStart = now.startOf('day').valueOf()
const initialEnd = now.endOf('day').valueOf()
const loading = ref(false)
const errorMessage = ref('')
const rows = ref([])
const nextCursor = ref(null)
const cursorStack = ref([null])
const pageIndex = ref(0)
const pageSize = ref(20)

const filters = reactive({
  dateRange: [initialStart, initialEnd],
  auth_result: 'all',
  user_type_code: null,
  fail_reason_code: null,
  user_name: '',
  terminal_ip: '',
  terminal_mac: '',
})

const resultOptions = [
  { label: '全部结果', value: 'all' },
  { label: '认证成功', value: 'success' },
  { label: '认证失败', value: 'failure' },
]
const userTypeOptions = [
  { label: '短信用户', value: 1 },
  { label: '微信用户', value: 5 },
  { label: '普通访客', value: 20 },
]
const failureOptions = [
  { label: '密码错误（101）', value: 101 },
  { label: '账号锁定（105）', value: 105 },
  { label: '账号过期（106）', value: 106 },
  { label: 'MAC 不匹配（111）', value: 111 },
  { label: '认证超时（116）', value: 116 },
  { label: '验证码错误（642）', value: 642 },
]
const pageSizeOptions = [20, 50, 101].map((value) => ({ label: String(value), value }))
const failureLabels = Object.fromEntries(
  failureOptions.map((item) => [item.value, item.label.split('（')[0]])
)

const successCount = computed(() => rows.value.filter((item) => item.auth_result_code === 0).length)
const failureCount = computed(() => rows.value.filter((item) => item.auth_result_code !== 0).length)

function renderTag(label, type) {
  return h(NTag, { type, bordered: false, size: 'small', round: true }, { default: () => label })
}

function authMethod(row) {
  if (row.user_type_code === 1) return '短信'
  if (row.user_type_code === 5) return '微信'
  if (row.user_name.startsWith('kio')) return '取号机'
  if (row.user_name.startsWith('bp_')) return '登机牌'
  if (row.user_name.startsWith('pas')) return '护照'
  return '访客'
}

const columns = [
  {
    title: '认证时间',
    key: 'authenticated_at',
    width: 170,
    render: (row) => dayjs(row.authenticated_at).format('YYYY-MM-DD HH:mm:ss'),
  },
  { title: '脱敏账号', key: 'user_name', width: 150, ellipsis: { tooltip: true } },
  {
    title: '认证方式',
    key: 'auth_method',
    width: 100,
    render: (row) => renderTag(authMethod(row), 'info'),
  },
  { title: '终端 IP', key: 'terminal_ip', width: 130 },
  { title: '终端 MAC', key: 'terminal_mac', width: 165 },
  { title: 'SSID', key: 'access_ssid', width: 150, ellipsis: { tooltip: true } },
  { title: '用户组', key: 'user_group_name', width: 100 },
  {
    title: '认证结果',
    key: 'auth_result_code',
    width: 100,
    render: (row) =>
      renderTag(
        row.auth_result_code === 0 ? '成功' : '失败',
        row.auth_result_code === 0 ? 'success' : 'error'
      ),
  },
  {
    title: '失败原因',
    key: 'fail_reason_code',
    width: 150,
    render: (row) =>
      row.auth_result_code === 0
        ? '—'
        : failureLabels[row.fail_reason_code] || `代码 ${row.fail_reason_code}`,
  },
]

function disableFutureDate(timestamp) {
  return timestamp > dayjs().endOf('day').valueOf()
}

function buildPayload() {
  const [start, end] = filters.dateRange || []
  if (!start || !end) throw new Error('请选择查询时间范围')
  if (end - start > 7 * 24 * 60 * 60 * 1000) throw new Error('查询时间范围不能超过 7 天')
  const payload = {
    start_time: dayjs(start).toISOString(),
    end_time: dayjs(end).toISOString(),
    auth_result: filters.auth_result,
    page_size: pageSize.value,
    cursor: cursorStack.value[pageIndex.value],
  }
  for (const key of ['user_type_code', 'fail_reason_code']) {
    if (filters[key] !== null) payload[key] = filters[key]
  }
  for (const key of ['user_name', 'terminal_ip', 'terminal_mac']) {
    const value = filters[key].trim()
    if (value) payload[key] = value
  }
  return payload
}

async function fetchLogs(reset = false) {
  if (reset) {
    cursorStack.value = [null]
    pageIndex.value = 0
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await api.getWifiRadiusLogs(buildPayload())
    rows.value = response.data?.items || []
    nextCursor.value = response.data?.next_cursor || null
  } catch (error) {
    rows.value = []
    nextCursor.value = null
    errorMessage.value = error?.message || '准入日志查询失败'
  } finally {
    loading.value = false
  }
}

async function goNext() {
  if (!nextCursor.value) return
  cursorStack.value.push(nextCursor.value)
  pageIndex.value += 1
  await fetchLogs()
}

async function goPrevious() {
  if (pageIndex.value === 0) return
  cursorStack.value.pop()
  pageIndex.value -= 1
  await fetchLogs()
}

function resetFilters() {
  filters.dateRange = [dayjs().startOf('day').valueOf(), dayjs().endOf('day').valueOf()]
  filters.auth_result = 'all'
  filters.user_type_code = null
  filters.fail_reason_code = null
  filters.user_name = ''
  filters.terminal_ip = ''
  filters.terminal_mac = ''
  pageSize.value = 20
  fetchLogs(true)
}

onMounted(() => fetchLogs(true))
</script>

<style scoped>
.logs-page {
  min-height: 100%;
  padding: 24px;
  border-radius: 14px;
  background: #f3f7fa;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
}

.eyebrow {
  margin: 0 0 5px;
  color: #1976a8;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.16em;
}

.page-header h1 {
  margin: 0;
  color: #122f47;
  font-size: 28px;
}

.page-header p {
  margin: 7px 0 0;
  color: #72889a;
  font-size: 13px;
}

.header-status {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 12px;
  border: 1px solid #e5d7b5;
  border-radius: 6px;
  background: #fffaf0;
  color: #9a6c00;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 10px;
  font-weight: 700;
}

.pulse {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #e5a100;
  box-shadow: 0 0 0 4px rgb(229 161 0 / 13%);
}

.filter-card,
.table-card {
  border: 1px solid #d8e2e9;
  border-radius: 10px;
  box-shadow: 0 7px 22px rgb(32 61 82 / 5%);
}

.filter-grid {
  display: grid;
  grid-template-columns: 1.4fr repeat(3, minmax(150px, 0.65fr));
  gap: 14px;
}

.filter-grid label {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.filter-grid label > span {
  color: #60778a;
  font-size: 11px;
  font-weight: 600;
}

.wide-field {
  grid-row: span 2;
}

.filter-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 17px;
  padding-top: 15px;
  border-top: 1px dashed #d8e2e9;
}

.filter-actions p {
  margin: 0;
  color: #8294a2;
  font-size: 11px;
}

.metric-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  overflow: hidden;
  margin: 16px 0;
  border: 1px solid #d8e2e9;
  border-radius: 8px;
  background: #d8e2e9;
}

.metric-strip > div {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  padding: 13px 16px;
  background: #fff;
}

.metric-strip span {
  color: #788d9d;
  font-size: 11px;
}

.metric-strip strong {
  color: #173d59;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 20px;
}

.metric-strip .success {
  color: #168957;
}

.metric-strip .danger {
  color: #d13b43;
}

.table-card :deep(.n-card__content) {
  padding: 0;
}

.table-card :deep(.n-data-table-th) {
  background: #edf3f7;
  color: #3e5b70;
  font-size: 12px;
}

.cursor-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 13px 16px;
  border-top: 1px solid #e1e8ed;
}

.cursor-footer > div {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #788d9d;
  font-size: 11px;
}

.cursor-footer .n-select {
  width: 78px;
}

@media (max-width: 1100px) {
  .filter-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .wide-field {
    grid-row: auto;
  }
}

@media (max-width: 680px) {
  .logs-page {
    padding: 14px;
  }

  .page-header,
  .filter-actions {
    align-items: flex-start;
    flex-direction: column;
  }

  .filter-grid,
  .metric-strip {
    grid-template-columns: 1fr;
  }

  .filter-actions .n-space {
    justify-content: flex-end;
    width: 100%;
  }
}
</style>
