import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || null)
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  function setAuth(authData) {
    token.value = authData.token
    user.value = authData.user
    localStorage.setItem('token', authData.token)
    localStorage.setItem('user', JSON.stringify(authData.user))
  }

  function clearAuth() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  const isAuthenticated = () => !!token.value

  return {
    token,
    user,
    setAuth,
    clearAuth,
    isAuthenticated
  }
})
