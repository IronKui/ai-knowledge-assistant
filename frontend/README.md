# AI 知识库 · 前端

企业级 RAG 知识库问答系统的前端，基于 **Vue 3 + Vite**。

> 需要配合后端服务运行：[rag-backend](https://github.com/IronKui/my-first-rag)

## ✨ 功能

- **登录 / 注册**：JWT 鉴权
- **智能问答**：对话式交互，支持多轮上下文
- **多会话管理**：会话列表、历史加载、重命名、删除
- **文件管理**：上传（账号级 / 会话级）、列表、删除
- **模式切换**：学习 / 面试 / 角色扮演

## 🛠 技术栈

| 模块 | 技术 |
|:---|:---|
| 框架 | Vue 3（`<script setup>` 组合式 API）|
| 构建工具 | Vite |
| 状态管理 | Vue `ref` / `computed`（组件内）|
| 通信 | 原生 `fetch` 封装（`src/api.js`）|

## 📁 项目结构

```
src/
├── main.js              # 入口
├── App.vue              # 根组件（登录态管理）
├── api.js               # API 封装（统一带 token）
├── style.css            # 全局设计变量与基础样式
├── views/
│   ├── LoginView.vue    # 登录 / 注册页
│   └── ChatView.vue     # 主界面（状态管理）
└── components/
    ├── Sidebar.vue      # 侧边栏（会话 / 文件 / 模式）
    └── MessageArea.vue  # 聊天区（消息 / 输入 / 上传）
```

## 🚀 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

启动后访问 http://localhost:5173

## ⚙️ 后端地址配置

后端接口地址在 `src/api.js` 中配置（默认 `http://localhost:8000`）：

```js
const BASE_URL = 'http://localhost:8000'
```

请确保后端已启动，且配置了 CORS 允许跨域。

## 🧩 组件通信

- 父组件通过 **props** 向子组件传递数据
- 子组件通过 **emit** 向父组件发送事件
- 例如：`Sidebar` 接收 `sessions`（props），点击会话时 `emit('switch-session', id)` 通知 `ChatView` 加载历史
