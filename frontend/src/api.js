// API 封装：统一处理请求和 token
// 留空表示走同源相对路径（/api/...），由 vite 的 proxy 转发到后端。
// 如需指向其他后端，构建时设置环境变量 VITE_API_BASE=http://host:port
const BASE_URL = import.meta.env.VITE_API_BASE || ''

let authToken = null

export function setToken(token) {
  authToken = token
}

export function getToken() {
  return authToken
}

// JSON 请求（带 token）
export async function api(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`
  const res = await fetch(BASE_URL + path, { ...options, headers })
  return res.json()
}

// 上传文件（FormData + token）
export async function uploadFile(formData) {
  const headers = {}
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`
  const res = await fetch(BASE_URL + '/api/upload', { method: 'POST', headers, body: formData })
  return res.json()
}
