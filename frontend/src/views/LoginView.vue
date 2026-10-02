<script setup>
// 登录 / 注册页
import { ref } from 'vue'
import { api } from '../api'

const emit = defineEmits(['login-success'])

const isRegister = ref(false)   // false=登录, true=注册
const username = ref('')
const password = ref('')
const nickname = ref('')
const errorMsg = ref('')

function toggleMode() {
  isRegister.value = !isRegister.value
  errorMsg.value = ''
}

async function handleSubmit() {
  errorMsg.value = ''
  const url = isRegister.value ? '/api/register' : '/api/login'
  const body = isRegister.value
    ? { username: username.value, password: password.value, nickname: nickname.value }
    : { username: username.value, password: password.value }

  try {
    const data = await api(url, { method: 'POST', body: JSON.stringify(body) })
    if (data.code === 0) {
      emit('login-success', username.value, data.data.token)
    } else {
      errorMsg.value = data.message
    }
  } catch (e) {
    errorMsg.value = '请求失败：' + e.message
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="brand">◆</div>
      <h1>AI 知识库</h1>
      <p class="subtitle">企业级 RAG 知识库问答系统</p>

      <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

      <label>用户名</label>
      <input v-model="username" placeholder="请输入用户名" @keyup.enter="handleSubmit" />

      <label>密码</label>
      <input v-model="password" type="password" placeholder="请输入密码" @keyup.enter="handleSubmit" />

      <template v-if="isRegister">
        <label>昵称（可选）</label>
        <input v-model="nickname" placeholder="展示昵称" @keyup.enter="handleSubmit" />
      </template>

      <button class="submit-btn" @click="handleSubmit">
        {{ isRegister ? '注册' : '登录' }}
      </button>

      <p class="switch">
        <span>{{ isRegister ? '已有账号？' : '还没有账号？' }}</span>
        <a @click="toggleMode">{{ isRegister ? '立即登录' : '立即注册' }}</a>
      </p>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: var(--bg);
  background-image:
    radial-gradient(circle at 20% 10%, rgba(99, 102, 241, 0.07), transparent 42%),
    radial-gradient(circle at 85% 90%, rgba(6, 182, 212, 0.06), transparent 42%);
}

.auth-card {
  width: 396px;
  padding: 44px 40px 38px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  animation: cardIn 0.5s var(--ease) both;
}

@keyframes cardIn {
  from { opacity: 0; transform: translateY(12px) scale(0.99); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}

.brand {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 46px;
  margin-bottom: 22px;
  background: var(--primary);
  color: #fff;
  font-size: 18px;
  border-radius: var(--radius);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.3);
}

h1 {
  font-size: 23px;
  font-weight: 650;
  letter-spacing: -0.02em;
  margin-bottom: 6px;
}

.subtitle {
  font-size: 13.5px;
  color: var(--text-3);
  margin-bottom: 30px;
}

.error {
  font-size: 13px;
  color: var(--danger);
  margin-bottom: 12px;
  min-height: 18px;
}

label {
  display: block;
  font-size: 12.5px;
  font-weight: 550;
  color: var(--text-2);
  margin-bottom: 7px;
}

input {
  width: 100%;
  padding: 11px 13px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-family: var(--font);
  font-size: 14px;
  color: var(--text);
  margin-bottom: 18px;
  outline: none;
  transition: border-color 0.18s var(--ease), box-shadow 0.18s var(--ease);
}

input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-ring);
}

input::placeholder { color: var(--text-3); }

.submit-btn {
  width: 100%;
  padding: 12px;
  margin-top: 6px;
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  font-family: var(--font);
  font-size: 14px;
  font-weight: 550;
  cursor: pointer;
  transition: background 0.18s var(--ease), transform 0.12s var(--ease);
}

.submit-btn:hover { background: var(--primary-hover); }
.submit-btn:active { transform: scale(0.985); }

.switch {
  text-align: center;
  margin-top: 22px;
  font-size: 13.5px;
  color: var(--text-3);
}

.switch a {
  color: var(--primary);
  cursor: pointer;
  font-weight: 550;
  margin-left: 4px;
}

.switch a:hover { text-decoration: underline; }
</style>
