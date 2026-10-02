<script setup>
// 根组件：管理登录状态，切换登录页 / 主界面
import { ref } from 'vue'
import { setToken } from './api'
import LoginView from './views/LoginView.vue'
import ChatView from './views/ChatView.vue'

const loggedIn = ref(false)
const username = ref('')

// 登录成功回调
function onLoginSuccess(name, token) {
  setToken(token)
  username.value = name
  loggedIn.value = true
}

// 退出登录
function onLogout() {
  loggedIn.value = false
  username.value = ''
  setToken(null)
}
</script>

<template>
  <LoginView v-if="!loggedIn" @login-success="onLoginSuccess" />
  <ChatView v-else :username="username" @logout="onLogout" />
</template>
