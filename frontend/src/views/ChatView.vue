<script setup>
// 主界面：管理会话、文件、消息状态
import { ref, computed, onMounted } from 'vue'
import { api, uploadFile } from '../api'
import Sidebar from '../components/Sidebar.vue'
import MessageArea from '../components/MessageArea.vue'

const props = defineProps({ username: String })
const emit = defineEmits(['logout'])

// ====== 状态 ======
const sessions = ref([])          // 会话列表
const files = ref([])             // 文件列表
const messages = ref([])          // 当前会话消息
const currentSessionId = ref(null)
const currentMode = ref('default')
const currentScope = ref('account')
const loading = ref(false)

// 当前会话标题（给顶部栏显示）
const currentTitle = computed(() => {
  const s = sessions.value.find(x => x.session_id === currentSessionId.value)
  return s ? s.session_name : '新会话'
})

// ====== 初始化：加载会话 + 文件 ======
onMounted(async () => {
  await loadSessions()
  await loadFiles()
})

async function loadSessions() {
  const data = await api('/api/sessions')
  if (data.code === 0) sessions.value = data.data
}

async function loadFiles() {
  const data = await api('/api/files')
  if (data.code === 0) files.value = data.data
}

// ====== 会话操作 ======
function newChat() {
  currentSessionId.value = null
  messages.value = []
}

async function switchSession(id) {
  currentSessionId.value = id
  const data = await api(`/api/sessions/${id}/history`)
  if (data.code === 0) messages.value = data.data.messages
}

async function renameSession(id, name) {
  const data = await api(`/api/sessions/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ session_name: name })
  })
  if (data.code === 0) await loadSessions()
}

async function deleteSession(id) {
  const data = await api(`/api/sessions/${id}`, { method: 'DELETE' })
  if (data.code === 0) {
    if (currentSessionId.value === id) newChat()
    await loadSessions()
  }
}

// ====== 发送消息 ======
async function sendMessage(question) {
  messages.value.push({ role: 'user', content: question })
  loading.value = true
  try {
    const data = await api('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        question,
        mode: currentMode.value,
        session_id: currentSessionId.value || 'default'
      })
    })
    if (data.code === 0) {
      messages.value.push({ role: 'assistant', content: data.data.answer })
      // 新会话：保存 id 并刷新列表
      if (data.data.session_id && !currentSessionId.value) {
        currentSessionId.value = data.data.session_id
        await loadSessions()
      }
    } else {
      messages.value.push({ role: 'error', content: data.message })
    }
  } catch (e) {
    messages.value.push({ role: 'error', content: '请求失败：' + e.message })
  } finally {
    loading.value = false
  }
}

// ====== 文件上传 ======
async function handleUpload(file) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('session_id', currentSessionId.value || 'default')
  formData.append('scope', currentScope.value)
  const data = await uploadFile(formData)
  if (data.code === 0) {
    messages.value.push({ role: 'assistant', content: `${data.message}（${data.data.chunk_count} 个文本块）` })
    await loadFiles()
  } else if (data.code === 1) {
    messages.value.push({ role: 'assistant', content: data.message })
  } else {
    messages.value.push({ role: 'error', content: '上传失败：' + data.message })
  }
}

async function deleteFile(id) {
  const data = await api(`/api/files/${id}`, { method: 'DELETE' })
  if (data.code === 0) await loadFiles()
  else alert(data.message)
}
</script>

<template>
  <div class="chat-layout">
    <Sidebar
      :username="props.username"
      :sessions="sessions"
      :files="files"
      :current-session-id="currentSessionId"
      :current-mode="currentMode"
      :current-scope="currentScope"
      @new-chat="newChat"
      @switch-session="switchSession"
      @rename-session="renameSession"
      @delete-session="deleteSession"
      @delete-file="deleteFile"
      @change-mode="m => currentMode = m"
      @change-scope="s => currentScope = s"
      @logout="emit('logout')"
    />
    <MessageArea
      :messages="messages"
      :loading="loading"
      :title="currentTitle"
      :mode="currentMode"
      @send="sendMessage"
      @upload="handleUpload"
    />
  </div>
</template>

<style scoped>
.chat-layout {
  display: flex;
  height: 100vh;
  background: var(--bg);
}
</style>
