<template>
  <AppPage :show-footer="false">
    <section class="health-page">
      <header class="health-hero">
        <div>
          <p class="eyebrow">SZX · WIFI OPERATIONS</p>
          <h1>外部服务状态</h1>
          <p class="subtitle">实时检查认证网关与关键基础设施，数据不会在管理台长期留存。</p>
        </div>
        <div class="hero-actions">
          <div class="updated-at">
            <span>最近检查</span>
            <strong>{{ lastUpdated || '尚未检查' }}</strong>
          </div>
          <n-button type="primary" :loading="loading" @click="loadHealth">
            <template #icon>
              <TheIcon icon="ph:arrows-clockwise-bold" />
            </template>
            立即刷新
          </n-button>
        </div>
      </header>

      <n-alert v-if="errorMessage" type="error" title="健康状态获取失败" closable class="mb-18">
        {{ errorMessage }}
      </n-alert>

      <n-spin :show="loading && services.length === 0">
        <div class="service-grid">
          <article v-for="service in services" :key="service.key" class="service-card">
            <div class="card-topline">
              <div class="service-identity">
                <span class="service-icon" :class="`is-${service.status}`">
                  <TheIcon :icon="service.icon" />
                </span>
                <div>
                  <p class="service-code">{{ service.code }}</p>
                  <h2>{{ service.name }}</h2>
                </div>
              </div>
              <n-tag :type="statusMeta[service.status].type" :bordered="false" round>
                {{ statusMeta[service.status].label }}
              </n-tag>
            </div>

            <div class="signal-line" :class="`is-${service.status}`">
              <span></span><span></span><span></span><span></span><span></span>
            </div>

            <dl class="metrics">
              <div>
                <dt>响应延时</dt>
                <dd>{{ service.latency }}<small> ms</small></dd>
              </div>
              <div>
                <dt>配置状态</dt>
                <dd class="textual">{{ service.configured ? '已配置' : '未配置' }}</dd>
              </div>
              <div v-if="service.mode">
                <dt>运行模式</dt>
                <dd class="textual">{{ service.mode.toUpperCase() }}</dd>
              </div>
            </dl>

            <footer>
              <span class="status-dot" :class="`is-${service.status}`"></span>
              {{ service.message }}
            </footer>
          </article>
        </div>
      </n-spin>

      <aside class="legend-panel">
        <div>
          <span class="legend-mark"></span>
          <strong>状态判定</strong>
        </div>
        <p>健康：依赖可正常响应；波动：配置或业务异常；离线：连接失败或调用超时。</p>
        <p class="mock-note">当前 NCE 使用 Mock，Mock 状态不代表真实机场网络设备状态。</p>
      </aside>
    </section>
  </AppPage>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import dayjs from 'dayjs'

import api from '@/api'
import TheIcon from '@/components/icon/TheIcon.vue'

const loading = ref(false)
const errorMessage = ref('')
const healthData = ref({})
const lastUpdated = ref('')

const statusMeta = {
  healthy: { label: '健康', type: 'success' },
  degraded: { label: '波动', type: 'warning' },
  down: { label: '离线', type: 'error' },
}

const services = computed(() => {
  const definitions = [
    { key: 'nce', name: 'iMaster NCE-Campus', code: 'NCE NORTHBOUND', icon: 'ph:wifi-high-bold' },
    { key: 'redis', name: '认证事务缓存', code: 'REDIS 7.2', icon: 'ph:database-bold' },
  ]
  return definitions
    .filter((definition) => healthData.value[definition.key])
    .map((definition) => {
      const health = healthData.value[definition.key]
      return {
        ...definition,
        status: statusMeta[health.status] ? health.status : 'down',
        configured: Boolean(health.configured),
        latency: Number.isFinite(health.latency_ms) ? health.latency_ms : 0,
        message: health.message || '状态未知',
        mode: health.mode || '',
      }
    })
})

async function loadHealth() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await api.getWifiHealth()
    healthData.value = response.data || {}
    lastUpdated.value = dayjs().format('YYYY-MM-DD HH:mm:ss')
  } catch (error) {
    errorMessage.value = error?.message || '无法连接健康检查接口'
  } finally {
    loading.value = false
  }
}

onMounted(loadHealth)
</script>

<style scoped>
.health-page {
  --navy: #102a43;
  --blue: #1677ff;
  --line: #d7e2ee;
  min-height: 100%;
  padding: 24px;
  border-radius: 14px;
  background: linear-gradient(90deg, rgb(16 42 67 / 3%) 1px, transparent 1px) 0 0 / 32px 32px,
    linear-gradient(rgb(16 42 67 / 3%) 1px, transparent 1px) 0 0 / 32px 32px, #f4f8fc;
}

.health-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 28px;
  margin-bottom: 24px;
  padding: 28px 30px;
  border-left: 5px solid var(--blue);
  border-radius: 4px 12px 12px 4px;
  background: linear-gradient(118deg, #102a43, #173f68 72%, #1769aa);
  color: #fff;
  box-shadow: 0 18px 42px rgb(16 42 67 / 16%);
}

.eyebrow,
.service-code {
  margin: 0 0 7px;
  color: #7cc7ff;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.16em;
}

.health-hero h1 {
  margin: 0;
  font-size: 30px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.subtitle {
  margin: 9px 0 0;
  color: rgb(255 255 255 / 68%);
  font-size: 14px;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 20px;
}

.updated-at {
  display: grid;
  gap: 3px;
  text-align: right;
}

.updated-at span {
  color: rgb(255 255 255 / 56%);
  font-size: 11px;
}

.updated-at strong {
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 13px;
}

.service-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.service-card {
  padding: 22px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgb(255 255 255 / 94%);
  box-shadow: 0 8px 24px rgb(37 68 96 / 7%);
}

.card-topline,
.service-identity {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.service-identity {
  justify-content: flex-start;
}

.service-icon {
  display: grid;
  width: 48px;
  height: 48px;
  place-items: center;
  border-radius: 10px;
  background: #e8f3ff;
  color: var(--blue);
  font-size: 25px;
}

.service-icon.is-degraded {
  background: #fff4d6;
  color: #d58a00;
}

.service-icon.is-down {
  background: #ffe8e8;
  color: #d9363e;
}

.service-code {
  margin-bottom: 3px;
  color: #7791aa;
  letter-spacing: 0.1em;
}

.service-card h2 {
  margin: 0;
  color: var(--navy);
  font-size: 18px;
}

.signal-line {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 4px;
  margin: 22px 0;
}

.signal-line span {
  height: 3px;
  border-radius: 3px;
  background: #1aaa67;
}

.signal-line.is-degraded span:nth-child(n + 4),
.signal-line.is-down span {
  background: #e8edf2;
}

.signal-line.is-degraded span:nth-child(-n + 3) {
  background: #e5a100;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin: 0;
}

.metrics div {
  padding: 12px;
  border-radius: 8px;
  background: #f5f8fb;
}

.metrics dt {
  color: #7b8fa3;
  font-size: 11px;
}

.metrics dd {
  margin: 5px 0 0;
  color: var(--navy);
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 20px;
  font-weight: 700;
}

.metrics dd.textual {
  font-family: inherit;
  font-size: 14px;
}

.metrics small {
  color: #8798aa;
  font-size: 11px;
  font-weight: 500;
}

.service-card footer {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 18px;
  padding-top: 15px;
  border-top: 1px solid #edf1f5;
  color: #60788f;
  font-size: 13px;
}

.status-dot,
.legend-mark {
  width: 8px;
  height: 8px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: #1aaa67;
  box-shadow: 0 0 0 4px rgb(26 170 103 / 12%);
}

.status-dot.is-degraded {
  background: #e5a100;
  box-shadow: 0 0 0 4px rgb(229 161 0 / 12%);
}

.status-dot.is-down {
  background: #d9363e;
  box-shadow: 0 0 0 4px rgb(217 54 62 / 12%);
}

.legend-panel {
  display: flex;
  align-items: center;
  gap: 18px;
  margin-top: 18px;
  padding: 14px 18px;
  border: 1px dashed #c5d4e3;
  border-radius: 10px;
  color: #667f96;
  font-size: 12px;
}

.legend-panel div {
  display: flex;
  align-items: center;
  gap: 9px;
  color: var(--navy);
  white-space: nowrap;
}

.legend-panel p {
  margin: 0;
}

.mock-note {
  margin-left: auto !important;
  color: #ad6800;
}

@media (max-width: 900px) {
  .health-hero,
  .legend-panel {
    align-items: flex-start;
    flex-direction: column;
  }

  .hero-actions,
  .service-grid {
    width: 100%;
  }

  .service-grid {
    grid-template-columns: 1fr;
  }

  .mock-note {
    margin-left: 0 !important;
  }
}

@media (max-width: 560px) {
  .health-page {
    padding: 14px;
  }

  .health-hero {
    padding: 22px;
  }

  .hero-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .updated-at {
    text-align: left;
  }
}
</style>
