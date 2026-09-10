<template>
  <AppPage :show-footer="false">
    <section class="online-page">
      <header class="online-header">
        <div>
          <p class="eyebrow">SZX · LIVE TERMINALS</p>
          <h1>在线用户</h1>
          <p>NCE 实时在线终端代理视图，所有账号与设备标识均由服务端脱敏。</p>
        </div>
        <div class="live-control">
          <span class="live-dot"></span>
          <div>
            <small>最近刷新</small><strong>{{ updatedAt || '等待首次查询' }}</strong>
          </div>
          <n-button type="primary" :loading="loading" @click="loadUsers(false)">
            <template #icon><TheIcon icon="ph:arrows-clockwise-bold" /></template>
            刷新
          </n-button>
        </div>
      </header>

      <n-alert type="info" :bordered="false" class="capability-alert">
        <template #icon><TheIcon icon="ph:shield-check-bold" /></template>
        当前只开放在线状态查看。NCE 踢线能力尚未完成真实接口和高级权限审批，因此操作入口默认关闭。
      </n-alert>
      <n-alert v-if="errorMessage" type="error" class="mt-16">{{ errorMessage }}</n-alert>

      <div class="metric-grid">
        <article>
          <span>全网在线</span><strong>{{ total }}</strong
          ><small>ACTIVE CLIENTS</small>
        </article>
        <article>
          <span>当前页终端</span><strong>{{ rows.length }}</strong
          ><small>VISIBLE ROWS</small>
        </article>
        <article>
          <span>短信 / 微信</span
          ><strong>{{ channelCounts.sms }} / {{ channelCounts.wechat }}</strong
          ><small>NATIVE CHANNELS</small>
        </article>
        <article>
          <span>访客账号</span><strong>{{ channelCounts.guest }}</strong
          ><small>GUEST ACCESS</small>
        </article>
      </div>

      <n-card :bordered="false" class="terminal-card">
        <div class="terminal-toolbar">
          <div class="toolbar-title">
            <span class="radar-icon"><TheIcon icon="ph:radar-bold" /></span>
            <div>
              <strong>终端雷达</strong><small>数据源：NCE {{ dataSource }}</small>
            </div>
          </div>
          <div class="filters">
            <n-input
              v-model:value="filters.user_name"
              clearable
              placeholder="搜索用户账号"
              @keypress.enter="loadUsers(true)"
            >
              <template #prefix><TheIcon icon="ph:user-focus-bold" /></template>
            </n-input>
            <n-input
              v-model:value="filters.user_group_id"
              clearable
              placeholder="用户组 ID"
              @keypress.enter="loadUsers(true)"
            />
            <n-button @click="resetFilters">重置</n-button>
            <n-button secondary type="primary" @click="loadUsers(true)">筛选</n-button>
          </div>
        </div>

        <n-data-table
          remote
          :columns="columns"
          :data="rows"
          :loading="loading"
          :row-key="(row) => row.id"
          :scroll-x="1250"
          :single-line="false"
          striped
        />

        <footer class="table-footer">
          <div class="auto-refresh">
            <n-switch v-model:value="autoRefresh" size="small" />
            <span>每 30 秒自动刷新</span>
          </div>
          <div class="pagination">
            <span>第 {{ page }} 页</span>
            <n-select
              v-model:value="pageSize"
              size="small"
              :options="pageSizeOptions"
              @update:value="loadUsers(true)"
            />
            <n-button size="small" :disabled="page <= 1 || loading" @click="goPrevious"
              >上一页</n-button
            >
            <n-button
              size="small"
              type="primary"
              :disabled="page * pageSize >= total || loading"
              @click="goNext"
            >
              下一页
            </n-button>
          </div>
        </footer>
      </n-card>
    </section>
  </AppPage>
</template>

<script setup>
import { computed, h, onMounted, onUnmounted, reactive, ref } from 'vue'
import dayjs from 'dayjs'
import { NTag } from 'naive-ui'

import api from '@/api'
import TheIcon from '@/components/icon/TheIcon.vue'

const loading = ref(false)
const errorMessage = ref('')
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const updatedAt = ref('')
const autoRefresh = ref(true)
const dataSource = ref('UNKNOWN')
let refreshTimer

const filters = reactive({ user_name: '', user_group_id: '' })
const pageSizeOptions = [20, 50, 100].map((value) => ({ label: `${value} 条/页`, value }))

const channelCounts = computed(() => ({
  sms: rows.value.filter((item) => item.user_type_code === 1).length,
  wechat: rows.value.filter((item) => item.user_type_code === 5).length,
  guest: rows.value.filter((item) => item.user_type_code === 20).length,
}))

function authMethod(row) {
  if (row.user_type_code === 1) return { label: '短信', type: 'success' }
  if (row.user_type_code === 5) return { label: '微信', type: 'info' }
  if (row.user_name.startsWith('kio')) return { label: '取号机', type: 'warning' }
  if (row.user_name.startsWith('bp_')) return { label: '登机牌', type: 'default' }
  if (row.user_name.startsWith('pas')) return { label: '护照', type: 'default' }
  return { label: '访客', type: 'default' }
}

function onlineDuration(connectedAt) {
  if (!connectedAt) return '—'
  const minutes = Math.max(0, dayjs().diff(dayjs(connectedAt), 'minute'))
  if (minutes < 60) return `${minutes} 分钟`
  return `${Math.floor(minutes / 60)} 小时 ${minutes % 60} 分`
}

const columns = [
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: () =>
      h(
        NTag,
        { type: 'success', bordered: false, round: true, size: 'small' },
        { default: () => '在线' }
      ),
  },
  { title: '脱敏账号', key: 'user_name', width: 160, ellipsis: { tooltip: true } },
  {
    title: '认证方式',
    key: 'auth_method',
    width: 100,
    render: (row) => {
      const method = authMethod(row)
      return h(
        NTag,
        { type: method.type, bordered: false, size: 'small' },
        { default: () => method.label }
      )
    },
  },
  { title: '终端 IP', key: 'terminal_ip', width: 130 },
  { title: '终端 MAC', key: 'terminal_mac', width: 165 },
  { title: 'SSID', key: 'access_ssid', width: 160, ellipsis: { tooltip: true } },
  { title: '用户组', key: 'user_group_name', width: 110 },
  {
    title: '上线时间',
    key: 'connected_at',
    width: 170,
    render: (row) =>
      row.connected_at ? dayjs(row.connected_at).format('YYYY-MM-DD HH:mm:ss') : '—',
  },
  {
    title: '在线时长',
    key: 'duration',
    width: 130,
    render: (row) => onlineDuration(row.connected_at),
  },
]

async function loadRuntimeMode() {
  try {
    const response = await api.getWifiRuntimeConfig()
    dataSource.value = String(response.data?.nce_mode || 'unknown').toUpperCase()
  } catch {
    dataSource.value = 'UNKNOWN'
  }
}

async function loadUsers(resetPage = false) {
  if (resetPage) page.value = 1
  loading.value = true
  errorMessage.value = ''
  const params = { page: page.value, page_size: pageSize.value }
  if (filters.user_name.trim()) params.user_name = filters.user_name.trim()
  if (filters.user_group_id.trim()) params.user_group_id = filters.user_group_id.trim()
  try {
    const response = await api.getWifiOnlineUsers(params)
    rows.value = response.data?.items || []
    total.value = response.data?.total || 0
    updatedAt.value = dayjs().format('HH:mm:ss')
  } catch (error) {
    rows.value = []
    total.value = 0
    errorMessage.value = error?.message || '在线用户查询失败'
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.user_name = ''
  filters.user_group_id = ''
  loadUsers(true)
}

async function goPrevious() {
  if (page.value <= 1) return
  page.value -= 1
  await loadUsers()
}

async function goNext() {
  if (page.value * pageSize.value >= total.value) return
  page.value += 1
  await loadUsers()
}

onMounted(() => {
  loadRuntimeMode()
  loadUsers(true)
  refreshTimer = window.setInterval(() => {
    if (autoRefresh.value && !loading.value) loadUsers(false)
  }, 30000)
})

onUnmounted(() => window.clearInterval(refreshTimer))
</script>

<style scoped>
.online-page {
  min-height: 100%;
  padding: 24px;
  border-radius: 14px;
  background: radial-gradient(circle at 92% 0%, rgb(24 144 255 / 8%), transparent 28%), #f2f7fa;
}

.online-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 18px;
}

.eyebrow {
  margin: 0 0 5px;
  color: #1582aa;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.16em;
}

.online-header h1 {
  margin: 0;
  color: #102f47;
  font-size: 28px;
}

.online-header p {
  margin: 7px 0 0;
  color: #71889a;
  font-size: 13px;
}

.live-control {
  display: flex;
  align-items: center;
  gap: 12px;
}

.live-control > div {
  display: grid;
  margin-right: 5px;
  text-align: right;
}

.live-control small {
  color: #8b9aa7;
  font-size: 9px;
  letter-spacing: 0.1em;
}

.live-control strong {
  color: #315269;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 12px;
}

.live-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #18a058;
  box-shadow: 0 0 0 5px rgb(24 160 88 / 10%);
  animation: live-pulse 2s infinite;
}

.capability-alert {
  border-left: 4px solid #2080b8;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin: 16px 0;
}

.metric-grid article {
  position: relative;
  overflow: hidden;
  padding: 17px 18px;
  border: 1px solid #d9e4eb;
  border-radius: 9px;
  background: #fff;
}

.metric-grid article::after {
  position: absolute;
  right: -15px;
  bottom: -25px;
  width: 70px;
  height: 70px;
  border: 12px solid rgb(32 128 184 / 6%);
  border-radius: 50%;
  content: '';
}

.metric-grid span,
.metric-grid small,
.metric-grid strong {
  display: block;
}

.metric-grid span {
  color: #708899;
  font-size: 11px;
}

.metric-grid strong {
  margin: 6px 0 2px;
  color: #123d59;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 24px;
}

.metric-grid small {
  color: #9aabb7;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 8px;
  letter-spacing: 0.08em;
}

.terminal-card {
  border: 1px solid #d6e2ea;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgb(31 65 88 / 6%);
}

.terminal-card :deep(.n-card__content) {
  padding: 0;
}

.terminal-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 16px;
  border-bottom: 1px solid #e0e8ee;
}

.toolbar-title,
.filters,
.auto-refresh,
.pagination {
  display: flex;
  align-items: center;
  gap: 9px;
}

.radar-icon {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 7px;
  background: #eaf6fb;
  color: #1686ad;
  font-size: 21px;
}

.toolbar-title strong,
.toolbar-title small {
  display: block;
}

.toolbar-title strong {
  color: #173a53;
  font-size: 13px;
}

.toolbar-title small {
  margin-top: 2px;
  color: #8ca0ae;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 9px;
}

.filters .n-input {
  width: 190px;
}

.terminal-card :deep(.n-data-table-th) {
  background: #edf4f7;
  color: #3e5e71;
  font-size: 12px;
}

.table-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 13px 16px;
  border-top: 1px solid #e0e8ee;
  color: #748a99;
  font-size: 11px;
}

.pagination .n-select {
  width: 100px;
}

@keyframes live-pulse {
  50% {
    box-shadow: 0 0 0 8px rgb(24 160 88 / 3%);
  }
}

@media (max-width: 1050px) {
  .metric-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .terminal-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .filters {
    flex-wrap: wrap;
    width: 100%;
  }
}

@media (max-width: 680px) {
  .online-page {
    padding: 14px;
  }

  .online-header,
  .live-control,
  .table-footer {
    align-items: flex-start;
    flex-direction: column;
  }

  .live-control > div {
    text-align: left;
  }

  .filters .n-input,
  .filters .n-button {
    width: 100%;
  }

  .metric-grid {
    grid-template-columns: 1fr;
  }

  .pagination {
    flex-wrap: wrap;
  }
}

@media (prefers-reduced-motion: reduce) {
  .live-dot {
    animation: none;
  }
}
</style>
