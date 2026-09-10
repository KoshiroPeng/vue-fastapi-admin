<template>
  <AppPage :show-footer="false">
    <section class="config-page">
      <header class="config-header">
        <div>
          <p class="eyebrow">SZX · RUNTIME MANIFEST</p>
          <h1>运行配置摘要</h1>
          <p>此页面仅展示当前实例的脱敏配置快照，不提供在线修改能力。</p>
        </div>
        <n-button secondary type="primary" :loading="loading" @click="loadConfig">
          <template #icon><TheIcon icon="ph:arrows-clockwise-bold" /></template>
          刷新摘要
        </n-button>
      </header>

      <n-alert type="warning" :bordered="false" class="readonly-alert">
        配置变更必须通过环境变量或 Secret
        管理平台完成，并通过滚动发布生效。页面不会返回任何密码、Token 或密钥原文。
      </n-alert>
      <n-alert v-if="errorMessage" type="error" class="mt-16">{{ errorMessage }}</n-alert>

      <n-spin :show="loading && !hasData">
        <div v-if="hasData" class="config-layout">
          <article class="identity-card manifest-card">
            <div class="section-heading">
              <span>01</span>
              <div>
                <small>INSTANCE</small>
                <h2>实例与 NCE 上下文</h2>
              </div>
            </div>
            <dl class="identity-grid">
              <div>
                <dt>运行环境</dt>
                <dd>{{ config.app_env }}</dd>
              </div>
              <div>
                <dt>WiFi SSID</dt>
                <dd>{{ config.wifi_ssid }}</dd>
              </div>
              <div>
                <dt>NCE 模式</dt>
                <dd>
                  <n-tag :type="config.nce_mode === 'mock' ? 'warning' : 'success'" size="small">{{
                    config.nce_mode
                  }}</n-tag>
                </dd>
              </div>
              <div>
                <dt>Mock 场景</dt>
                <dd>{{ config.nce_mock_scenario || '—' }}</dd>
              </div>
              <div class="wide">
                <dt>Site ID</dt>
                <dd>{{ config.nce_site_id || '未配置' }}</dd>
              </div>
              <div class="wide">
                <dt>访客用户组 ID</dt>
                <dd>{{ config.nce_guest_user_group_id || '未配置' }}</dd>
              </div>
            </dl>
          </article>

          <article class="manifest-card methods-card">
            <div class="section-heading">
              <span>02</span>
              <div>
                <small>AUTH CHANNELS</small>
                <h2>认证方式开关</h2>
              </div>
            </div>
            <div class="method-list">
              <div v-for="method in authMethods" :key="method.key" class="method-row">
                <span class="method-icon"><TheIcon :icon="method.icon" /></span>
                <div>
                  <strong>{{ method.label }}</strong
                  ><small>{{ method.note }}</small>
                </div>
                <n-tag :type="method.enabled ? 'success' : 'default'" :bordered="false" round>
                  {{ method.enabled ? '已启用' : '已停用' }}
                </n-tag>
              </div>
            </div>
          </article>

          <article class="manifest-card security-card">
            <div class="section-heading">
              <span>03</span>
              <div>
                <small>SECURITY POSTURE</small>
                <h2>敏感配置状态</h2>
              </div>
            </div>
            <div class="security-grid">
              <div v-for="item in securityItems" :key="item.key" :class="{ missing: !item.ready }">
                <span class="state-light"></span>
                <p>
                  <strong>{{ item.label }}</strong
                  ><small>{{ item.ready ? '已通过受控配置注入' : '尚未配置' }}</small>
                </p>
              </div>
            </div>
          </article>

          <article class="manifest-card limits-card">
            <div class="section-heading">
              <span>04</span>
              <div>
                <small>OPERATING LIMITS</small>
                <h2>网关运行参数</h2>
              </div>
            </div>
            <div class="limit-grid">
              <div v-for="item in limitItems" :key="item.label">
                <small>{{ item.label }}</small>
                <strong>{{ item.value }}</strong>
                <span>{{ item.unit }}</span>
              </div>
            </div>
          </article>
        </div>
      </n-spin>

      <footer class="config-footer">
        <span>READ ONLY</span>
        <p>快照时间：{{ updatedAt || '尚未获取' }}</p>
      </footer>
    </section>
  </AppPage>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import dayjs from 'dayjs'

import api from '@/api'
import TheIcon from '@/components/icon/TheIcon.vue'

const config = ref({})
const loading = ref(false)
const errorMessage = ref('')
const updatedAt = ref('')
const hasData = computed(() => Object.keys(config.value).length > 0)

const methodDefinitions = [
  { key: 'sms', label: '短信认证', note: 'NCE 原生短信链路', icon: 'ph:chat-circle-text-bold' },
  { key: 'wechat', label: '微信认证', note: '小程序 Portal 放行', icon: 'ph:wechat-logo-bold' },
  { key: 'boarding_pass', label: '登机牌认证', note: '三要素验证', icon: 'ph:airplane-tilt-bold' },
  {
    key: 'passport',
    label: '护照认证',
    note: 'OCR 与 MRZ 校验',
    icon: 'ph:identification-card-bold',
  },
  { key: 'kiosk', label: '取号机认证', note: '24 小时访客账号', icon: 'ph:printer-bold' },
]

const authMethods = computed(() =>
  methodDefinitions.map((item) => ({
    ...item,
    enabled: Boolean(config.value.auth_methods?.[item.key]),
  }))
)

const securityItems = computed(() => [
  { key: 'nce-api', label: 'NCE 北向地址', ready: config.value.nce_base_url_configured },
  { key: 'nce-portal', label: 'NCE Portal 地址', ready: config.value.nce_portal_url_configured },
  { key: 'nce-auth', label: 'NCE 接入凭据', ready: config.value.nce_credentials_configured },
  { key: 'nce-site', label: 'NCE 站点上下文', ready: config.value.nce_site_configured },
  { key: 'redis', label: 'Redis 连接', ready: config.value.redis_configured },
  { key: 'pii', label: 'PII 摘要密钥', ready: config.value.pii_hash_secret_configured },
  { key: 'kiosk', label: '取号机 HMAC 密钥', ready: config.value.kiosk_hmac_configured },
])

const limitItems = computed(() => [
  { label: 'NCE 超时', value: config.value.nce_timeout_ms, unit: 'ms' },
  { label: '认证事务 TTL', value: config.value.auth_transaction_ttl_seconds, unit: 's' },
  { label: 'Nonce TTL', value: config.value.nonce_ttl_seconds, unit: 's' },
  { label: '幂等 TTL', value: config.value.idempotency_ttl_seconds, unit: 's' },
  { label: 'IP 每分钟上限', value: config.value.rate_limit_per_ip, unit: '次' },
  { label: 'MAC 每分钟上限', value: config.value.rate_limit_per_mac, unit: '次' },
  { label: '取号机访客有效期', value: config.value.kiosk_guest_valid_minutes, unit: 'min' },
  { label: '取号机请求体上限', value: config.value.kiosk_max_body_bytes, unit: 'bytes' },
])

async function loadConfig() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await api.getWifiRuntimeConfig()
    config.value = response.data || {}
    updatedAt.value = dayjs().format('YYYY-MM-DD HH:mm:ss')
  } catch (error) {
    errorMessage.value = error?.message || '无法获取运行配置摘要'
  } finally {
    loading.value = false
  }
}

onMounted(loadConfig)
</script>

<style scoped>
.config-page {
  min-height: 100%;
  padding: 24px;
  border-radius: 14px;
  background: #f3f6f8;
  color: #16324a;
}

.config-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 10px 4px 22px;
  border-bottom: 1px solid #cad5df;
}

.eyebrow,
.section-heading small {
  margin: 0 0 5px;
  color: #2776a8;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.15em;
}

.config-header h1 {
  margin: 0;
  font-size: 29px;
}

.config-header p {
  margin: 8px 0 0;
  color: #6d8293;
}

.readonly-alert {
  margin-top: 18px;
  border-left: 4px solid #e5a100;
}

.config-layout {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 18px;
  margin-top: 18px;
}

.manifest-card {
  padding: 22px;
  border: 1px solid #d3dde5;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 8px 22px rgb(26 54 77 / 5%);
}

.section-heading {
  display: flex;
  align-items: center;
  gap: 13px;
  margin-bottom: 20px;
}

.section-heading > span {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border: 1px solid #b9cada;
  border-radius: 50%;
  color: #2776a8;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 11px;
  font-weight: 700;
}

.section-heading small {
  display: block;
  margin: 0;
}

.section-heading h2 {
  margin: 2px 0 0;
  font-size: 17px;
}

.identity-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px;
  overflow: hidden;
  margin: 0;
  border: 1px solid #dce4eb;
  border-radius: 7px;
  background: #dce4eb;
}

.identity-grid div {
  min-width: 0;
  padding: 13px 15px;
  background: #f8fafb;
}

.identity-grid .wide {
  grid-column: span 2;
}

.identity-grid dt,
.limit-grid small {
  color: #8193a2;
  font-size: 11px;
}

.identity-grid dd {
  overflow: hidden;
  margin: 5px 0 0;
  color: #193b55;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.method-list {
  display: grid;
  gap: 8px;
}

.method-row {
  display: grid;
  grid-template-columns: 38px 1fr auto;
  align-items: center;
  gap: 11px;
  padding: 10px;
  border-radius: 7px;
  background: #f7f9fb;
}

.method-icon {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border: 1px solid #d5e2ec;
  border-radius: 6px;
  background: #fff;
  color: #1769aa;
  font-size: 19px;
}

.method-row strong,
.method-row small {
  display: block;
}

.method-row strong {
  font-size: 13px;
}

.method-row small {
  margin-top: 2px;
  color: #8797a5;
  font-size: 10px;
}

.security-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.security-grid > div {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border: 1px solid #dce7df;
  border-radius: 7px;
  background: #f7fbf8;
}

.security-grid > div.missing {
  border-color: #eadfca;
  background: #fffbf3;
}

.state-light {
  width: 8px;
  height: 8px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: #18a058;
  box-shadow: 0 0 0 4px rgb(24 160 88 / 10%);
}

.missing .state-light {
  background: #d89400;
  box-shadow: 0 0 0 4px rgb(216 148 0 / 10%);
}

.security-grid p,
.security-grid strong,
.security-grid small {
  display: block;
  margin: 0;
}

.security-grid strong {
  font-size: 12px;
}

.security-grid small {
  margin-top: 3px;
  color: #8193a2;
  font-size: 10px;
}

.limit-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.limit-grid > div {
  min-width: 0;
  padding: 15px 12px;
  border-top: 3px solid #3d87b8;
  background: #f5f8fa;
}

.limit-grid strong {
  display: block;
  overflow: hidden;
  margin-top: 8px;
  color: #123b59;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 19px;
  text-overflow: ellipsis;
}

.limit-grid span {
  color: #8496a5;
  font-size: 10px;
}

.config-footer {
  display: flex;
  justify-content: space-between;
  margin-top: 18px;
  padding: 12px 4px;
  border-top: 1px solid #cad5df;
  color: #7d8f9d;
  font-size: 11px;
}

.config-footer span {
  color: #2776a8;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-weight: 700;
  letter-spacing: 0.16em;
}

.config-footer p {
  margin: 0;
}

@media (max-width: 1000px) {
  .config-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .config-page {
    padding: 14px;
  }

  .config-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .security-grid,
  .limit-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
