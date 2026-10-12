import { defineStore } from 'pinia'

export const useAuth = defineStore('auth', {
  state: () => ({
    access: localStorage.getItem('access_token') || '',
    refresh: localStorage.getItem('refresh_token') || '',
    nickname: localStorage.getItem('nickname') || '',
    joule: Number(localStorage.getItem('joule') || 0),
  }),
  actions: {
    setTokens(t: { access_token: string; refresh_token: string }) {
      this.access = t.access_token
      this.refresh = t.refresh_token
      localStorage.setItem('access_token', t.access_token)
      localStorage.setItem('refresh_token', t.refresh_token)
    },
    setProfile(nickname: string, joule: number) {
      this.nickname = nickname
      this.joule = joule
      localStorage.setItem('nickname', nickname)
      localStorage.setItem('joule', String(joule))
    },
    logout() {
      this.access = this.refresh = ''
      localStorage.clear()
    },
  },
})
