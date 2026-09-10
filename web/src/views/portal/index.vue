<template>
  <main class="portal-page">
    <header class="portal-header">
      <div class="brand">
        <span><TheIcon icon="ph:wifi-high-bold" /></span>
        <div><strong>深圳机场免费 WiFi</strong><small>SHENZHEN AIRPORT</small></div>
      </div>
      <n-tag v-if="isMock" type="warning" :bordered="false">MOCK</n-tag>
    </header>

    <section v-if="fatalError" class="fatal-state">
      <TheIcon icon="ph:wifi-slash-bold" />
      <h1>网络认证参数缺失</h1>
      <p>{{ fatalError }}</p>
      <n-button type="primary" @click="reloadPage">重新检测</n-button>
    </section>

    <template v-else>
      <section class="welcome-block">
        <p>WELCOME TO SZX</p>
        <h1>选择认证方式</h1>
        <span>完成认证后即可使用机场免费网络</span>
      </section>

      <section class="method-grid">
        <button
          v-for="method in methods"
          :key="method.key"
          :class="{ active: selectedMethod === method.key }"
          @click="selectedMethod = method.key"
        >
          <span><TheIcon :icon="method.icon" /></span><strong>{{ method.label }}</strong
          ><small>{{ method.note }}</small>
        </button>
      </section>

      <section class="auth-panel">
        <n-alert v-if="errorMessage" type="error" class="mb-16">{{ errorMessage }}</n-alert>
        <n-alert v-if="successMessage" type="success" class="mb-16">{{ successMessage }}</n-alert>

        <form v-if="selectedMethod === 'sms'" class="auth-form" @submit.prevent="submitSms">
          <div class="panel-heading">
            <span>01</span>
            <div>
              <h2>短信认证</h2>
              <p>由 NCE 原生短信认证链路完成网络放行</p>
            </div>
          </div>
          <n-input
            id="username"
            v-model:value="sms.phone"
            size="large"
            placeholder="请输入手机号"
            maxlength="20"
          />
          <div class="code-row">
            <n-input
              id="password"
              v-model:value="sms.code"
              size="large"
              placeholder="请输入验证码"
              maxlength="6"
            />
            <n-button
              id="getSmscodeBtn"
              size="large"
              :disabled="countdown > 0"
              @click="sendSmsCode"
              >{{ countdown ? `${countdown}s` : '获取验证码' }}</n-button
            >
          </div>
          <n-button id="loginBtn" attr-type="submit" type="primary" size="large" block
            >连接网络</n-button
          >
          <p v-if="isMock" class="mock-hint">Mock 模式验证码：123456</p>
        </form>

        <form
          v-else-if="selectedMethod === 'boarding'"
          class="auth-form"
          @submit.prevent="submitBoardingPass"
        >
          <div class="panel-heading">
            <span>02</span>
            <div>
              <h2>登机牌认证</h2>
              <p>适用于深圳机场国内出港且已值机旅客</p>
            </div>
          </div>
          <n-date-picker
            v-model:formatted-value="boarding.flightDate"
            value-format="yyyy-MM-dd"
            type="date"
            size="large"
          />
          <div class="two-columns">
            <n-input
              v-model:value="boarding.flightNo"
              size="large"
              placeholder="航班号，如 CA1234"
            /><n-input v-model:value="boarding.seatNo" size="large" placeholder="座位号，如 16A" />
          </div>
          <n-input
            v-model:value="boarding.documentLast4"
            size="large"
            placeholder="购票/值机证件号码后 4 位"
            maxlength="4"
          />
          <n-button attr-type="submit" type="primary" size="large" block :loading="loading"
            >验证并连接</n-button
          >
          <p v-if="isMock" class="mock-hint">Mock 数据：CA1234 / 16A / 5678</p>
        </form>

        <section v-else-if="selectedMethod === 'passport'" class="auth-form">
          <div class="panel-heading">
            <span>03</span>
            <div>
              <h2>护照认证</h2>
              <p>图像仅在内存中识别，不会保存到磁盘</p>
            </div>
          </div>
          <label class="upload-zone">
            <input type="file" accept="image/jpeg,image/png" @change="selectPassport" />
            <TheIcon icon="ph:camera-bold" /><strong>{{
              passportFile?.name || '拍摄或选择护照资料页'
            }}</strong
            ><small>JPG / PNG，最大 4MB</small>
          </label>
          <n-button
            type="primary"
            size="large"
            block
            :loading="loading"
            :disabled="!passportFile"
            @click="submitPassport"
            >识别并连接</n-button
          >
        </section>

        <form
          v-else-if="selectedMethod === 'kiosk'"
          class="auth-form"
          @submit.prevent="submitKiosk"
        >
          <div class="panel-heading">
            <span>04</span>
            <div>
              <h2>取号机账号认证</h2>
              <p>请输入现场自助取号机打印的小票账号和密码</p>
            </div>
          </div>
          <n-input
            id="username"
            v-model:value="kiosk.username"
            size="large"
            placeholder="小票账号"
          />
          <n-input
            id="password"
            v-model:value="kiosk.password"
            type="password"
            size="large"
            placeholder="小票密码"
            show-password-on="mousedown"
          />
          <n-button id="loginBtn" attr-type="submit" type="primary" size="large" block
            >连接网络</n-button
          >
          <p v-if="isMock" class="mock-hint">Mock 模式填写任意非空账号和密码</p>
        </form>

        <section v-else class="auth-form">
          <div class="panel-heading">
            <span>05</span>
            <div>
              <h2>微信小程序认证</h2>
              <p>小程序完成 NCE Portal 放行后，本页面自动更新状态</p>
            </div>
          </div>
          <div class="wechat-block">
            <TheIcon icon="ph:wechat-logo-bold" />
            <p>{{ wechatStatus }}</p>
            <small v-if="wechatTxId">事务号：{{ wechatTxId }}</small>
          </div>
          <n-button
            type="primary"
            color="#18a058"
            size="large"
            block
            :loading="loading"
            @click="startWechat"
            >打开微信小程序</n-button
          >
        </section>
      </section>

      <footer class="portal-footer">
        <span>{{ context.ssid }}</span
        ><span>服务热线 0755-23456789</span>
      </footer>
    </template>
  </main>
</template>

<script setup>
import { onUnmounted, reactive, ref } from 'vue'
import dayjs from 'dayjs'
import api from '@/api'
import TheIcon from '@/components/icon/TheIcon.vue'

const isMock = import.meta.env.VITE_PORTAL_MOCK === 'true'
const params = new URLSearchParams(window.location.search)
const context = reactive({
  clientIp: params.get('wlanuserip') || (isMock ? '10.1.2.30' : ''),
  clientMac: params.get('wlanusermac') || (isMock ? 'AA-BB-CC-DD-EE-30' : ''),
  ssid: params.get('ssid') || 'Airport-Free-WiFi',
})
const fatalError = ref(
  !context.clientIp || !context.clientMac ? '请断开并重新连接机场 WiFi 后再试。' : ''
)
const selectedMethod = ref('sms')
const loading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const countdown = ref(0)
const sms = reactive({ phone: '', code: '' })
const kiosk = reactive({ username: '', password: '' })
const boarding = reactive({
  flightDate: dayjs().format('YYYY-MM-DD'),
  flightNo: '',
  seatNo: '',
  documentLast4: '',
})
const passportFile = ref(null)
const wechatTxId = ref('')
const wechatStatus = ref('点击下方按钮发起认证')
let countdownTimer
let pollingTimer

const methods = [
  { key: 'sms', label: '短信', note: '手机号验证码', icon: 'ph:chat-circle-text-bold' },
  { key: 'boarding', label: '登机牌', note: '国内出港旅客', icon: 'ph:airplane-tilt-bold' },
  { key: 'passport', label: '护照', note: '国际旅客', icon: 'ph:identification-card-bold' },
  { key: 'kiosk', label: '取号机', note: '小票账号', icon: 'ph:printer-bold' },
  { key: 'wechat', label: '微信', note: '小程序认证', icon: 'ph:wechat-logo-bold' },
]

function resetMessages() {
  errorMessage.value = ''
  successMessage.value = ''
}
function reloadPage() {
  window.location.reload()
}
function sendSmsCode() {
  if (!/^1\d{10}$/.test(sms.phone)) {
    errorMessage.value = '请输入正确的手机号'
    return
  }
  resetMessages()
  countdown.value = 60
  countdownTimer = window.setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) window.clearInterval(countdownTimer)
  }, 1000)
}
function submitSms() {
  resetMessages()
  if (!/^1\d{10}$/.test(sms.phone) || !/^\d{6}$/.test(sms.code)) {
    errorMessage.value = '请输入正确的手机号和 6 位验证码'
    return
  }
  if (isMock && sms.code !== '123456') {
    errorMessage.value = 'Mock 验证码错误'
    return
  }
  successMessage.value = '短信认证成功，网络连接已放行（Mock）'
}
function submitKiosk() {
  resetMessages()
  if (!kiosk.username.trim() || !kiosk.password) {
    errorMessage.value = '请输入小票账号和密码'
    return
  }
  successMessage.value = '账号认证成功，网络连接已放行（Mock）'
  kiosk.password = ''
}
async function submitBoardingPass() {
  resetMessages()
  loading.value = true
  try {
    const response = await api.verifyBoardingPass({ ...boarding, ...context })
    successMessage.value = `登机牌验证成功，临时账号 ${response.data.tempUsername} 已创建`
  } catch (error) {
    errorMessage.value = error?.message || '登机牌认证失败'
  } finally {
    loading.value = false
  }
}
function selectPassport(event) {
  resetMessages()
  const file = event.target.files?.[0]
  if (!file) return
  if (!['image/jpeg', 'image/png'].includes(file.type) || file.size > 4 * 1024 * 1024) {
    errorMessage.value = '请选择不超过 4MB 的 JPG 或 PNG 图片'
    passportFile.value = null
    return
  }
  passportFile.value = file
}
async function submitPassport() {
  resetMessages()
  loading.value = true
  try {
    const response = await api.verifyPassport(passportFile.value, context)
    successMessage.value = `护照识别成功：${response.data.passportNoMasked}`
    passportFile.value = null
  } catch (error) {
    errorMessage.value = error?.message || '护照认证失败'
  } finally {
    loading.value = false
  }
}
async function startWechat() {
  resetMessages()
  loading.value = true
  try {
    const response = await api.startWechatAuth(context)
    wechatTxId.value = response.data.authTxId
    wechatStatus.value = '等待小程序完成 NCE Portal 放行…'
    pollingTimer = window.setInterval(pollWechatStatus, 2000)
    if (isMock) window.setTimeout(() => api.mockCompleteWechatAuth(wechatTxId.value), 700)
    window.setTimeout(() => {
      if (pollingTimer) {
        window.clearInterval(pollingTimer)
        pollingTimer = null
        if (!successMessage.value) wechatStatus.value = '认证等待超时，请重试或选择其他方式'
      }
    }, 60000)
  } catch (error) {
    errorMessage.value = error?.message || '微信认证发起失败'
  } finally {
    loading.value = false
  }
}
async function pollWechatStatus() {
  if (!wechatTxId.value) return
  try {
    const response = await api.getWechatAuthStatus(wechatTxId.value)
    wechatStatus.value = response.data.status
    if (response.data.status === 'SUCCESS') {
      successMessage.value = '微信认证成功，网络已放行'
      window.clearInterval(pollingTimer)
      pollingTimer = null
    }
    if (response.data.status === 'FAILED') {
      errorMessage.value = '微信认证未完成，请重试'
      window.clearInterval(pollingTimer)
      pollingTimer = null
    }
  } catch {
    wechatStatus.value = '状态查询暂时失败，正在重试…'
  }
}
onUnmounted(() => {
  window.clearInterval(countdownTimer)
  window.clearInterval(pollingTimer)
})
</script>

<style scoped>
.portal-page {
  min-height: 100vh;
  padding: 20px;
  background: linear-gradient(150deg, #eaf5ff, #f7fbff 45%, #dceeff);
  color: #17324a;
  font-family: 'Microsoft YaHei', sans-serif;
}
.portal-header,
.brand,
.method-grid,
.two-columns,
.portal-footer {
  display: flex;
}
.portal-header {
  align-items: center;
  justify-content: space-between;
  max-width: 760px;
  margin: auto;
}
.brand {
  align-items: center;
  gap: 10px;
}
.brand > span {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 10px;
  background: #1677ff;
  color: #fff;
  font-size: 24px;
}
.brand strong,
.brand small {
  display: block;
}
.brand small {
  color: #7890a4;
  font: 9px 'Cascadia Code', monospace;
  letter-spacing: 0.12em;
}
.welcome-block {
  max-width: 760px;
  margin: 44px auto 22px;
}
.welcome-block p {
  margin: 0;
  color: #1677ff;
  font: 700 10px 'Cascadia Code', monospace;
  letter-spacing: 0.18em;
}
.welcome-block h1 {
  margin: 6px 0;
  font-size: 30px;
}
.welcome-block span {
  color: #73899b;
}
.method-grid {
  max-width: 760px;
  margin: auto;
  gap: 10px;
}
.method-grid button {
  display: grid;
  flex: 1;
  gap: 4px;
  padding: 14px 10px;
  border: 1px solid #d2e0eb;
  border-radius: 12px;
  background: #fff;
  color: #557084;
  text-align: left;
  cursor: pointer;
}
.method-grid button > span {
  font-size: 23px;
}
.method-grid strong,
.method-grid small {
  display: block;
}
.method-grid small {
  color: #93a3af;
  font-size: 10px;
}
.method-grid button.active {
  border-color: #1677ff;
  background: #edf6ff;
  color: #1268c4;
  box-shadow: 0 8px 22px rgb(22 119 255 / 12%);
}
.auth-panel {
  max-width: 760px;
  margin: 14px auto;
  padding: 26px;
  border: 1px solid #d3e1eb;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 18px 45px rgb(41 81 112 / 10%);
}
.auth-form {
  display: grid;
  gap: 15px;
}
.panel-heading {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}
.panel-heading > span {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 50%;
  background: #eaf4ff;
  color: #1677ff;
  font: 700 11px 'Cascadia Code', monospace;
}
.panel-heading h2,
.panel-heading p {
  margin: 0;
}
.panel-heading h2 {
  font-size: 18px;
}
.panel-heading p {
  margin-top: 3px;
  color: #8295a4;
  font-size: 11px;
}
.code-row,
.two-columns {
  gap: 10px;
}
.code-row {
  display: grid;
  grid-template-columns: 1fr 130px;
}
.two-columns > * {
  flex: 1;
}
.mock-hint {
  margin: 0;
  color: #ad7600;
  font-size: 10px;
  text-align: center;
}
.upload-zone {
  display: grid;
  padding: 32px;
  place-items: center;
  border: 1px dashed #8db9da;
  border-radius: 10px;
  background: #f4faff;
  color: #407697;
  cursor: pointer;
}
.upload-zone input {
  display: none;
}
.upload-zone > svg {
  font-size: 34px;
}
.upload-zone strong {
  margin-top: 8px;
}
.upload-zone small {
  color: #8aa0b0;
}
.wechat-block {
  display: grid;
  padding: 32px;
  place-items: center;
  border-radius: 10px;
  background: #f1faf5;
}
.wechat-block > svg {
  color: #18a058;
  font-size: 48px;
}
.wechat-block p {
  margin: 10px 0 4px;
}
.wechat-block small {
  color: #82968b;
}
.portal-footer {
  max-width: 760px;
  margin: 18px auto;
  justify-content: space-between;
  color: #7990a2;
  font-size: 10px;
}
.fatal-state {
  display: grid;
  max-width: 420px;
  margin: 20vh auto;
  padding: 40px;
  place-items: center;
  border-radius: 16px;
  background: #fff;
  text-align: center;
}
.fatal-state > svg {
  color: #d13b43;
  font-size: 48px;
}
.fatal-state h1 {
  margin-bottom: 0;
}
.fatal-state p {
  color: #758a9a;
}
@media (max-width: 600px) {
  .portal-page {
    padding: 16px;
  }
  .welcome-block {
    margin-top: 34px;
  }
  .method-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
  }
  .auth-panel {
    padding: 20px;
  }
  .two-columns {
    flex-direction: column;
  }
  .code-row {
    grid-template-columns: 1fr 112px;
  }
  .portal-footer {
    gap: 8px;
    flex-direction: column;
  }
  .welcome-block h1 {
    font-size: 26px;
  }
}
@media (prefers-reduced-motion: reduce) {
  * {
    scroll-behavior: auto !important;
  }
}
</style>
