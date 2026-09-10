<template>
  <section class="login-page">
    <div class="login-visual" :style="{ backgroundImage: `url(${bgImg})` }">
      <div class="brand">
        <span class="brand-mark">
          <icon-ph-cloud-check-bold />
        </span>
        <span>{{ $t('app_name') }}</span>
      </div>
    </div>

    <main class="login-panel">
      <div class="login-card">
        <header class="login-header">
          <span class="login-icon">
            <icon-ph-cloud-check-bold />
          </span>
          <h1>欢迎登录</h1>
          <p>{{ $t('app_name') }}</p>
        </header>

        <div class="login-form">
          <n-input
            v-model:value="loginInfo.username"
            autofocus
            size="large"
            placeholder="请输入账号"
            :maxlength="20"
            :theme-overrides="inputThemeOverrides"
            @keypress.enter="handleLogin"
          >
            <template #prefix>
              <icon-ph-user-circle class="field-icon" />
            </template>
          </n-input>

          <n-input
            v-model:value="loginInfo.password"
            size="large"
            type="password"
            show-password-on="mousedown"
            placeholder="请输入密码"
            :maxlength="20"
            :theme-overrides="inputThemeOverrides"
            @keypress.enter="handleLogin"
          >
            <template #prefix>
              <icon-ph-lock-key class="field-icon" />
            </template>
          </n-input>

          <n-button
            class="login-button"
            color="#1677ff"
            size="large"
            block
            :loading="loading"
            @click="handleLogin"
          >
            {{ $t('views.login.text_login') }}
          </n-button>
        </div>
      </div>
    </main>
  </section>
</template>

<script setup>
import { lStorage, setToken } from '@/utils'
import bgImg from '@/assets/images/login_cloud_platform.png'
import api from '@/api'
import { addDynamicRoutes } from '@/router'
import { useI18n } from 'vue-i18n'

const router = useRouter()
const { query } = useRoute()
const { t } = useI18n({ useScope: 'global' })

const loginInfo = ref({
  username: '',
  password: '',
})

const inputThemeOverrides = {
  borderFocus: '1px solid #1677ff',
  boxShadowFocus: '0 0 0 2px rgb(22 119 255 / 14%)',
  caretColor: '#1677ff',
}

initLoginInfo()

function initLoginInfo() {
  const localLoginInfo = lStorage.get('loginInfo')
  if (localLoginInfo) {
    loginInfo.value.username = localLoginInfo.username || ''
    loginInfo.value.password = localLoginInfo.password || ''
  }
}

const loading = ref(false)
async function handleLogin() {
  const { username, password } = loginInfo.value
  if (!username || !password) {
    $message.warning(t('views.login.message_input_username_password'))
    return
  }
  try {
    loading.value = true
    $message.loading(t('views.login.message_verifying'))
    const res = await api.login({ username, password: password.toString() })
    $message.success(t('views.login.message_login_success'))
    setToken(res.data.access_token)
    await addDynamicRoutes()
    if (query.redirect) {
      const path = query.redirect
      console.log('path', { path, query })
      Reflect.deleteProperty(query, 'redirect')
      router.push({ path, query })
    } else {
      router.push('/')
    }
  } catch (e) {
    console.error('login error', e.error)
  }
  loading.value = false
}
</script>

<style scoped>
.login-page {
  --login-blue: #1677ff;
  display: grid;
  min-height: 100vh;
  grid-template-columns: minmax(0, 68%) minmax(380px, 32%);
  overflow: hidden;
  background: var(--login-blue);
  font-family: "Segoe UI Variable", "Microsoft YaHei", sans-serif;
}

.login-visual {
  position: relative;
  min-height: 100vh;
  background-position: center;
  background-size: cover;
  animation: visual-enter 800ms ease-out both;
}

.login-visual::after {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, rgb(9 110 231 / 4%) 60%, rgb(22 119 255 / 38%));
  content: "";
  pointer-events: none;
}

.brand {
  position: absolute;
  z-index: 1;
  top: 42px;
  left: 48px;
  display: flex;
  align-items: center;
  gap: 12px;
  color: #fff;
  font-size: 20px;
  font-weight: 600;
  text-shadow: 0 2px 12px rgb(0 74 170 / 24%);
}

.brand-mark,
.login-icon {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border: 1px solid rgb(255 255 255 / 48%);
  border-radius: 8px;
  background: rgb(255 255 255 / 20%);
  font-size: 25px;
  backdrop-filter: blur(8px);
}

.login-panel {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 40px;
  background: var(--login-blue);
}

.login-card {
  width: min(100%, 420px);
  padding: 48px 42px;
  border: 1px solid rgb(255 255 255 / 62%);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 24px 60px rgb(0 62 145 / 22%);
  animation: card-enter 620ms 120ms ease-out both;
}

.login-header {
  margin-bottom: 36px;
  text-align: center;
}

.login-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto 18px;
  border-color: #dbeafe;
  background: #eff6ff;
  color: var(--login-blue);
  font-size: 27px;
  backdrop-filter: none;
}

.login-header h1 {
  margin: 0;
  color: #17233d;
  font-size: 26px;
  font-weight: 650;
  line-height: 1.35;
}

.login-header p {
  margin: 9px 0 0;
  color: #8792a8;
  font-size: 14px;
}

.login-form {
  display: grid;
  gap: 22px;
}

.login-form :deep(.n-input) {
  height: 48px;
  border-radius: 5px;
  background: #f8faff;
}

.login-form :deep(.n-input__input-el) {
  height: 46px;
  font-size: 15px;
}

.field-icon {
  margin-right: 4px;
  color: #98a4b8;
  font-size: 19px;
}

.login-button {
  height: 48px;
  margin-top: 4px;
  border-radius: 5px;
  font-size: 16px;
  font-weight: 600;
  box-shadow: 0 10px 22px rgb(22 119 255 / 25%);
}

@keyframes visual-enter {
  from {
    opacity: 0;
    transform: scale(1.025);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes card-enter {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 900px) {
  .login-page {
    display: block;
    position: relative;
  }

  .login-visual {
    position: absolute;
    inset: 0;
    background-position: 46% center;
  }

  .brand {
    top: 24px;
    left: 24px;
    padding: 7px 12px 7px 7px;
    border-radius: 8px;
    background: rgb(0 77 174 / 28%);
    backdrop-filter: blur(8px);
  }

  .login-panel {
    position: relative;
    z-index: 2;
    padding: 96px 24px 36px;
    background: rgb(9 92 196 / 52%);
  }

  .login-card {
    padding: 40px 30px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .login-visual,
  .login-card {
    animation: none;
  }
}
</style>
