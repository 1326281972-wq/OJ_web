import axios from 'axios'

/** 统一响应结构（docs/api.md）：{ code, message, data }，成功 code=0 */
export interface ApiResp<T> {
  code: number
  message: string
  data: T
}

const http = axios.create({ baseURL: '/api/v1', timeout: 20000 })

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('oj_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (resp) => {
    const body = resp.data as ApiResp<unknown>
    if (body && typeof body.code === 'number' && body.code !== 0) {
      handleAuthError(body.code)
      return Promise.reject(new Error(body.message || 'request failed'))
    }
    return resp
  },
  (err) => {
    const body = err.response?.data as ApiResp<unknown> | undefined
    const msg = body?.message || err.message || 'network error'
    handleAuthError(body?.code ?? (err.response?.status === 401 ? 40101 : 0))
    return Promise.reject(new Error(msg))
  },
)

function handleAuthError(code: number) {
  if (code === 40101) {
    localStorage.removeItem('oj_token')
    localStorage.removeItem('oj_user')
    if (location.pathname !== '/login') location.href = '/login'
  }
}

export default http
