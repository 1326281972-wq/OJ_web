import { defineStore } from 'pinia'
import { login as apiLogin, register as apiRegister, type UserInfo } from '../api/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('oj_token') || '',
    user: JSON.parse(localStorage.getItem('oj_user') || 'null') as UserInfo | null,
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
  },
  actions: {
    setSession(token: string, user: UserInfo) {
      this.token = token
      this.user = user
      localStorage.setItem('oj_token', token)
      localStorage.setItem('oj_user', JSON.stringify(user))
    },
    async login(user_id: string, password: string) {
      const r = await apiLogin(user_id, password)
      this.setSession(r.access_token, r.user)
    },
    /** 注册成功后自动登录（主路径：注册 → 登录 → 题库） */
    async register(user_id: string, password: string, nickname: string, email?: string) {
      await apiRegister(user_id, password, nickname, email)
      await this.login(user_id, password)
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('oj_token')
      localStorage.removeItem('oj_user')
    },
  },
})
