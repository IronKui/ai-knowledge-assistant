// API 封装：统一处理请求和 token
const BASE_URL = 'http://localhost:8000'

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
