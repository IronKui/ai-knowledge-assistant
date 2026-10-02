<script setup>
// 聊天区：消息列表 + 输入框 + 文件上传
import { ref, nextTick, watch } from 'vue'

const props = defineProps({
  messages: Array,
  loading: Boolean,
  title: String,
  mode: String
})

const MODE_NAMES = { default: '默认', learning: '学习模式', interview: '面试模式', roleplay: '角色扮演' }
const emit = defineEmits(['send', 'upload'])

const input = ref('')
const fileInput = ref(null)
const messagesBox = ref(null)

// 新消息时自动滚到底部
watch(() => props.messages.length, async () => {
  await nextTick()
  if (messagesBox.value) messagesBox.value.scrollTop = messagesBox.value.scrollHeight
})

function send() {
  const text = input.value.trim()
  if (!text || props.loading) return
  emit('send', text)
  input.value = ''
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

function pickFile() {
  fileInput.value.click()
}

function onFileChange(e) {
  const file = e.target.files[0]
  if (file) emit('upload', file)
  e.target.value = ''
}
</script>

<template>
  <main class="main">
    <header class="msg-header">
      <span class="chat-title">{{ props.title || '新会话' }}</span>
      <span class="chat-mode">{{ MODE_NAMES[props.mode] || '默认' }}</span>
    </header>
    <div class="messages" ref="messagesBox">
      <div v-if="messages.length === 0" class="empty">
        <div class="icon">◆</div>
        <div>上传文档或输入问题，开始使用知识库</div>
      </div>
      <div
        v-for="(m, i) in messages"
        :key="i"
        class="message"
        :class="m.role"
      >{{ m.content }}</div>
      <div v-if="loading" class="message loading">思考中...</div>
    </div>

    <div class="input-area">
      <input ref="fileInput" type="file" style="display:none" accept=".pdf,.docx,.md,.txt" @change="onFileChange" />
      <button class="upload-btn" @click="pickFile" title="上传文件">＋</button>
      <textarea
        v-model="input"
        placeholder="输入你的问题…（Enter 发送，Shift+Enter 换行）"
        @keydown="onKeydown"
      ></textarea>
      <button class="send-btn" :disabled="loading" @click="send">发送</button>
    </div>
  </main>
</template>

<style scoped>
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--bg);
}

.msg-header {
  padding: 15px 28px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.chat-title {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-mode {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 550;
  color: var(--primary);
  background: var(--primary-soft);
  padding: 4px 11px;
  border-radius: 999px;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 28px 28px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: var(--text-3);
  gap: 14px;
  animation: fadeIn 0.5s var(--ease) both;
}

.empty .icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 62px;
  height: 62px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px;
  color: var(--primary);
  font-size: 24px;
  box-shadow: var(--shadow-sm);
}

@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

/* 消息气泡 */
.message {
  max-width: 68%;
  padding: 11px 15px;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  animation: msgIn 0.3s var(--ease) both;
}

@keyframes msgIn {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

.message.user {
  align-self: flex-end;
  background: var(--primary);
  color: #fff;
  border-radius: var(--radius) var(--radius) 3px var(--radius);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.22);
}

.message.assistant {
  align-self: flex-start;
  background: var(--surface);
  color: var(--text-2);
  border: 1px solid var(--border);
  border-radius: var(--radius) var(--radius) var(--radius) 3px;
  box-shadow: var(--shadow-sm);
}

.message.loading {
  align-self: flex-start;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius) var(--radius) var(--radius) 3px;
  color: var(--text-3);
  font-size: 13px;
  box-shadow: var(--shadow-sm);
}

.message.loading::after {
  content: "";
  display: inline-block;
  width: 3px;
  height: 3px;
  margin-left: 6px;
  border-radius: 50%;
  background: var(--text-3);
  animation: dots 1.2s infinite;
  box-shadow: 6px 0 0 var(--text-3), 12px 0 0 var(--text-3);
}

@keyframes dots {
  0%, 60%, 100% { opacity: 0.3; }
  30% { opacity: 1; }
}

.message.error {
  align-self: center;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: var(--danger);
  font-size: 13px;
  border-radius: var(--radius-sm);
  max-width: 80%;
}

/* 输入区 */
.input-area {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 8px 10px 8px 12px;
  margin: 0 28px 26px;
  box-shadow: var(--shadow-sm);
  transition: border-color 0.18s var(--ease), box-shadow 0.18s var(--ease);
}

.input-area:focus-within {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-ring);
}

.upload-btn {
  background: none;
  border: none;
  color: var(--text-3);
  font-size: 19px;
  line-height: 1;
  cursor: pointer;
  padding: 2px 5px;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}

.upload-btn:hover { color: var(--primary); background: var(--primary-soft); }

textarea {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  resize: none;
  font-family: var(--font);
  font-size: 14px;
  line-height: 1.6;
  color: var(--text);
  padding: 3px 0;
  min-height: 25px;
  max-height: 140px;
}

textarea::placeholder { color: var(--text-3); }

.send-btn {
  flex-shrink: 0;
  padding: 7px 16px;
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  font-family: var(--font);
  font-size: 13.5px;
  font-weight: 550;
  cursor: pointer;
  transition: background 0.18s var(--ease);
}

.send-btn:hover { background: var(--primary-hover); }
.send-btn:disabled { background: var(--surface-3); color: var(--text-3); cursor: not-allowed; }
</style>
