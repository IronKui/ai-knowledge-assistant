<script setup>
// 侧边栏：会话列表 / 文件列表 / 模式切换 / 用户信息
const props = defineProps({
  username: String,
  sessions: Array,
  files: Array,
  currentSessionId: String,
  currentMode: String,
  currentScope: String
})
const emit = defineEmits([
  'new-chat', 'switch-session', 'rename-session', 'delete-session',
  'delete-file', 'change-mode', 'change-scope', 'logout'
])

const MODES = [
  { key: 'default', name: '默认' },
  { key: 'learning', name: '学习模式' },
  { key: 'interview', name: '面试模式' },
  { key: 'roleplay', name: '角色扮演' }
]

function rename(id, oldName) {
  const name = prompt('输入新会话名称：', oldName)
  if (name && name.trim()) emit('rename-session', id, name.trim())
}

function confirmDelete(id) {
  if (confirm('确定删除该会话吗？')) emit('delete-session', id)
}

function confirmDeleteFile(id) {
  if (confirm('确定删除该文件吗？删除后无法恢复。')) emit('delete-file', id)
}
</script>

<template>
  <aside class="sidebar">
    <div class="header">
      <div class="app-name">🤖 AI 知识库</div>
      <div class="user-info">👤 {{ username }}</div>
    </div>

    <button class="new-btn" @click="emit('new-chat')">＋ 新建会话</button>

    <!-- 会话列表 -->
    <div class="section">
      <h3>会话</h3>
      <div
        v-for="s in sessions"
        :key="s.session_id"
        class="item"
        :class="{ active: s.session_id === currentSessionId }"
        @click="emit('switch-session', s.session_id)"
      >
        <span class="item-title">{{ s.session_name || '新会话' }}</span>
        <span class="menu" @click.stop="rename(s.session_id, s.session_name)">✎</span>
        <span class="menu" @click.stop="confirmDelete(s.session_id)">✕</span>
      </div>
    </div>

    <!-- 文件列表 -->
    <div class="section">
      <h3>知识库文件</h3>
      <div v-for="f in files" :key="f.id" class="item">
        <span class="item-title"><i class="file-dot">◆</i> {{ f.filename }}</span>
        <span class="menu" @click.stop="confirmDeleteFile(f.id)">✕</span>
      </div>
    </div>

    <!-- 模式切换 -->
    <div class="section mode-section">
      <h3>模式</h3>
      <button
        v-for="m in MODES"
        :key="m.key"
        class="mode-btn"
        :class="{ active: m.key === currentMode }"
        @click="emit('change-mode', m.key)"
      >{{ m.name }}</button>
    </div>

    <div class="footer">
      <span class="scope-label">上传范围：</span>
      <select :value="currentScope" @change="emit('change-scope', $event.target.value)">
        <option value="account">账号级</option>
        <option value="session">会话级</option>
      </select>
      <button class="logout" @click="emit('logout')">退出</button>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 264px;
  flex-shrink: 0;
  background: var(--surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
}

.header { padding: 18px 16px 12px; }

.app-name {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 15px;
  font-weight: 650;
  letter-spacing: -0.01em;
}

.app-name::before {
  content: "◆";
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 25px;
  height: 25px;
  background: var(--primary);
  color: #fff;
  font-size: 10px;
  border-radius: 7px;
}

.user-info {
  font-size: 12.5px;
  color: var(--text-3);
  margin-top: 9px;
  padding-left: 34px;
}

.new-btn {
  margin: 6px 12px 14px;
  padding: 9px 14px;
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  font-family: var(--font);
  font-size: 13.5px;
  font-weight: 550;
  cursor: pointer;
  transition: background 0.18s var(--ease), box-shadow 0.18s var(--ease);
}

.new-btn:hover {
  background: var(--primary-hover);
  box-shadow: 0 3px 10px rgba(99, 102, 241, 0.28);
}

.section { padding: 4px 12px; flex: 1; overflow-y: auto; min-height: 0; }

.section h3 {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: var(--text-3);
  text-transform: uppercase;
  padding: 10px 6px 8px;
}

.item {
  padding: 8px 10px;
  font-size: 13.5px;
  color: var(--text-2);
  cursor: pointer;
  border-radius: var(--radius-sm);
  margin-bottom: 1px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: background 0.15s var(--ease), color 0.15s var(--ease);
}

.item:hover { background: var(--surface-2); color: var(--text); }

.item.active {
  background: var(--primary-soft);
  color: var(--primary);
  font-weight: 550;
}

.item-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.file-dot {
  font-style: normal;
  font-size: 9px;
  color: var(--primary);
  opacity: 0.75;
  margin-right: 2px;
}

.menu {
  opacity: 0;
  color: var(--text-3);
  font-size: 13px;
  padding: 0 4px;
  border-radius: 4px;
  transition: opacity 0.15s, color 0.15s, background 0.15s;
}

.item:hover .menu { opacity: 1; }
.menu:hover { color: var(--text); background: var(--surface-3); }

.mode-section { flex: none; border-top: 1px solid var(--border); padding-top: 14px; }

.mode-btn {
  display: block;
  width: 100%;
  padding: 7px 10px;
  margin-bottom: 2px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-2);
  font-family: var(--font);
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s var(--ease), color 0.15s var(--ease);
}

.mode-btn:hover { background: var(--surface-2); color: var(--text); }

.mode-btn.active {
  background: var(--primary-soft);
  color: var(--primary);
  font-weight: 550;
}

.footer {
  padding: 12px 16px;
  border-top: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
}

.scope-label { color: var(--text-3); }

.footer select {
  flex: 1;
  padding: 4px 8px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-family: var(--font);
  font-size: 12px;
  color: var(--text-2);
  outline: none;
  cursor: pointer;
}

.logout {
  background: none;
  border: none;
  color: var(--text-3);
  font-family: var(--font);
  font-size: 12.5px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}

.logout:hover { color: var(--danger); background: #fef2f2; }
</style>
