import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '../api/client'
import router from '../router'

export type UserRole = 'Admin' | 'Operator' | 'Viewer'

export interface UserProfile {
  id: number
  username: string
  email: string
  role: UserRole
  is_staff: boolean
  is_superuser: boolean
  groups: string[]
}

interface LoginResponse {
  access: string
  refresh: string
  user: UserProfile
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const user = ref<UserProfile | null>((() => {
    try {
      const stored = localStorage.getItem('user_profile')
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  })())
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!token.value)
  const role = computed<UserRole>(() => user.value?.role || 'Viewer')
  const canEdit = computed(() => ['Operator', 'Admin'].includes(user.value?.role || ''))
  const isAdmin = computed(() => user.value?.role === 'Admin')

  async function login(credentials: { username: string; password: string }): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const res = await apiClient.post<LoginResponse>('/auth/token/', credentials)
      token.value = res.data.access
      refreshToken.value = res.data.refresh
      user.value = res.data.user

      localStorage.setItem('access_token', res.data.access)
      localStorage.setItem('refresh_token', res.data.refresh)
      localStorage.setItem('user_profile', JSON.stringify(res.data.user))
    } catch (err: any) {
      const detail =
        err.response?.data?.detail ||
        (typeof err.response?.data === 'string' ? err.response?.data : null) ||
        err.message ||
        'Invalid username or password'
      error.value = detail
      throw new Error(detail)
    } finally {
      loading.value = false
    }
  }

  async function fetchCurrentUser(): Promise<void> {
    if (!token.value) return
    try {
      const res = await apiClient.get<UserProfile>('/auth/user/')
      user.value = res.data
      localStorage.setItem('user_profile', JSON.stringify(res.data))
    } catch {
      // If fetching profile fails (e.g. invalid token), logout
      logout()
    }
  }

  function logout(): void {
    token.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_profile')
    router.push('/login')
  }

  return {
    token,
    refreshToken,
    user,
    loading,
    error,
    isAuthenticated,
    role,
    canEdit,
    isAdmin,
    login,
    fetchCurrentUser,
    logout,
  }
})
