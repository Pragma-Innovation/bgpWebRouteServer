<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { Radio, Lock, User, Eye, EyeOff, ShieldCheck } from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const showPassword = ref(false)
const errorMessage = ref<string | null>(null)
const isSubmitting = ref(false)

async function handleLogin() {
  if (!username.value.trim() || !password.value) {
    errorMessage.value = 'Please provide both username and password.'
    return
  }

  isSubmitting.value = true
  errorMessage.value = null

  try {
    await authStore.login({
      username: username.value.trim(),
      password: password.value,
    })
    const redirectPath = (route.query.redirect as string) || '/'
    router.push(redirectPath)
  } catch (err: any) {
    errorMessage.value = err.message || 'Authentication failed. Please verify credentials.'
  } finally {
    isSubmitting.value = false
  }
}

function fillDemoAccount(u: string, p: string) {
  username.value = u
  password.value = p
  errorMessage.value = null
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <!-- Header -->
      <div class="login-header">
        <div class="brand-badge">
          <Radio :size="28" />
        </div>
        <h2>bgpWebRouteServer</h2>
        <p class="subtitle">BGP Control Plane & Flowspec Mitigation</p>
      </div>

      <!-- Error Alert -->
      <div v-if="errorMessage" class="error-banner">
        <span>{{ errorMessage }}</span>
      </div>

      <!-- Form -->
      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label>Username</label>
          <div class="input-wrapper">
            <User :size="18" class="input-icon" />
            <input
              v-model="username"
              type="text"
              placeholder="e.g. operator"
              required
              autocomplete="username"
              autofocus
            />
          </div>
        </div>

        <div class="form-group">
          <label>Password</label>
          <div class="input-wrapper">
            <Lock :size="18" class="input-icon" />
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              placeholder="••••••••••••"
              required
              autocomplete="current-password"
            />
            <button
              type="button"
              class="btn-toggle-eye"
              @click="showPassword = !showPassword"
              tabindex="-1"
            >
              <EyeOff v-if="showPassword" :size="18" />
              <Eye v-else :size="18" />
            </button>
          </div>
        </div>

        <button type="submit" class="btn-submit" :disabled="isSubmitting">
          <span v-if="isSubmitting" class="spinner"></span>
          <span v-else>Sign In to Control Plane</span>
        </button>
      </form>

      <!-- Quick demo accounts helper -->
      <div class="demo-helpers">
        <div class="demo-title">
          <ShieldCheck :size="14" />
          <span>Role-Based Access Control</span>
        </div>
        <div class="demo-chips">
          <button
            type="button"
            class="chip chip-admin"
            @click="fillDemoAccount('admin', 'bgppassword123')"
            title="Click to auto-fill Admin credentials"
          >
            <strong>admin</strong> (Full Access)
          </button>
          <button
            type="button"
            class="chip chip-operator"
            @click="fillDemoAccount('operator', 'bgppassword123')"
            title="Click to auto-fill Operator credentials"
          >
            <strong>operator</strong> (Flowspec RW)
          </button>
          <button
            type="button"
            class="chip chip-viewer"
            @click="fillDemoAccount('viewer', 'bgppassword123')"
            title="Click to auto-fill Viewer credentials"
          >
            <strong>viewer</strong> (Read-Only)
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: radial-gradient(circle at 50% 20%, #1e293b 0%, #0f172a 100%);
}

.login-card {
  width: 100%;
  max-width: 440px;
  background: var(--color-surface-card);
  border: 1px solid var(--color-surface-border);
  border-radius: 16px;
  padding: 36px 32px;
  box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.5);
}

.login-header {
  text-align: center;
  margin-bottom: 28px;
}

.brand-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #3b82f6, #06b6d4);
  border-radius: 14px;
  color: #ffffff;
  margin-bottom: 16px;
  box-shadow: 0 8px 16px -4px rgba(59, 130, 246, 0.4);
}

.login-header h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 6px 0;
  letter-spacing: -0.02em;
}

.subtitle {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  margin: 0;
}

.error-banner {
  background-color: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #fca5a5;
  padding: 12px 14px;
  border-radius: 8px;
  font-size: 0.875rem;
  margin-bottom: 20px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-text-muted);
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 14px;
  color: var(--color-text-muted);
  pointer-events: none;
}

.input-wrapper input {
  width: 100%;
  padding: 11px 40px 11px 42px;
  background-color: var(--color-surface-input);
  border: 1px solid var(--color-surface-border);
  border-radius: 8px;
  color: #ffffff;
  font-size: 0.9375rem;
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.input-wrapper input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}

.btn-toggle-eye {
  position: absolute;
  right: 12px;
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
}

.btn-toggle-eye:hover {
  color: #ffffff;
}

.btn-submit {
  margin-top: 6px;
  padding: 12px;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  border: 1px solid #3b82f6;
  border-radius: 8px;
  color: #ffffff;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 46px;
}

.btn-submit:hover:not(:disabled) {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.demo-helpers {
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px solid var(--color-surface-border);
}

.demo-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
  margin-bottom: 10px;
}

.demo-chips {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.chip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 12px;
  background-color: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--color-surface-border);
  border-radius: 6px;
  color: var(--color-text-muted);
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: left;
}

.chip:hover {
  background-color: rgba(255, 255, 255, 0.07);
  border-color: #3b82f6;
  color: #ffffff;
}

.chip strong {
  color: #93c5fd;
}
</style>
