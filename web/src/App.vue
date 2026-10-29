<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useBgpStore } from './stores/bgpStore'
import { useAuthStore } from './stores/authStore'
import StatusBadge from './components/StatusBadge.vue'
import { LayoutDashboard, ShieldAlert, Network, Settings, Radio, User, LogOut, Database, Layers, Megaphone } from 'lucide-vue-next'

const route = useRoute()
const bgpStore = useBgpStore()
const authStore = useAuthStore()

onMounted(() => {
  if (authStore.isAuthenticated) {
    authStore.fetchCurrentUser()
    bgpStore.fetchStatus()
  }
})
</script>

<template>
  <!-- Fullscreen Login View without shell -->
  <RouterView v-if="route.path === '/login'" />

  <!-- Authenticated Application Shell -->
  <div v-else class="app-container">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-icon">
          <Radio :size="20" />
        </div>
        <div class="brand-text">
          <span class="brand-title">bgpWebRouteServer</span>
          <span class="brand-subtitle">Gabu Reborn</span>
        </div>
      </div>

      <nav class="nav-links">
        <RouterLink to="/" class="nav-item" :class="{ active: route.path === '/' }">
          <LayoutDashboard :size="18" />
          <span>Dashboard</span>
        </RouterLink>

        <RouterLink to="/prefixes" class="nav-item" :class="{ active: route.path.startsWith('/prefixes') }">
          <Database :size="18" />
          <span>Prefix Inventory</span>
        </RouterLink>

        <RouterLink to="/pseudo-ribs" class="nav-item" :class="{ active: route.path.startsWith('/pseudo-ribs') }">
          <Layers :size="18" />
          <span>Pseudo-RIBs</span>
        </RouterLink>

        <RouterLink to="/announcements" class="nav-item" :class="{ active: route.path.startsWith('/announcements') }">
          <Megaphone :size="18" />
          <span>Announcements</span>
        </RouterLink>

        <RouterLink to="/flowspec" class="nav-item" :class="{ active: route.path.startsWith('/flowspec') }">
          <ShieldAlert :size="18" />
          <span>Flowspec Rules</span>
        </RouterLink>

        <RouterLink to="/peers" class="nav-item" :class="{ active: route.path.startsWith('/peers') }">
          <Network :size="18" />
          <span>BGP Peers</span>
        </RouterLink>

        <RouterLink to="/settings" class="nav-item" :class="{ active: route.path.startsWith('/settings') }">
          <Settings :size="18" />
          <span>Architecture & Stack</span>
        </RouterLink>
      </nav>

      <div class="sidebar-footer">
        <div class="backend-tag">
          <span class="text-xs text-muted">Backend Engine</span>
          <span class="font-mono text-xs text-white truncate" :title="bgpStore.status?.backend || 'Loading...'">
            {{ bgpStore.status?.backend?.split(' ')[0] || 'MockBgpBackend' }}
          </span>
        </div>
      </div>
    </aside>

    <!-- Main Content Shell -->
    <div class="main-content">
      <header class="topbar">
        <div class="topbar-left">
          <span class="text-muted text-xs uppercase tracking-wider">BGP Control Plane</span>
        </div>
        <div class="topbar-right">
          <!-- BGP Router Status -->
          <StatusBadge
            v-if="bgpStore.status"
            :status="bgpStore.status.ready ? 'online' : 'offline'"
            :label="bgpStore.status.backend?.includes('Mock') ? 'Mock BGP Active' : 'Live GoBGP'"
          />

          <!-- Authenticated User Profile & RBAC Role -->
          <div v-if="authStore.isAuthenticated" class="user-badge">
            <div class="user-avatar">
              <User :size="14" />
            </div>
            <span class="username">{{ authStore.user?.username || 'Operator' }}</span>
            <span class="role-pill" :class="authStore.role.toLowerCase()">
              {{ authStore.role }}
            </span>
            <button class="btn-logout" @click="authStore.logout" title="Sign Out">
              <LogOut :size="16" />
            </button>
          </div>
        </div>
      </header>

      <main class="page-body">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.brand {
  height: 64px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  border-bottom: 1px solid var(--color-surface-border);
}
.brand-icon {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #3b82f6, #06b6d4);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
}
.brand-text {
  display: flex;
  flex-direction: column;
}
.brand-title {
  font-weight: 700;
  font-size: 0.9375rem;
  letter-spacing: -0.01em;
  color: #ffffff;
}
.brand-subtitle {
  font-size: 0.6875rem;
  color: var(--color-accent);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.nav-links {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 16px 12px;
  flex: 1;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 8px;
  color: var(--color-text-muted);
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.15s ease;
}
.nav-item:hover {
  background-color: rgba(255, 255, 255, 0.05);
  color: var(--color-text-main);
}
.nav-item.active {
  background-color: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  font-weight: 600;
}
.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--color-surface-border);
}
.backend-tag {
  background-color: rgba(255, 255, 255, 0.03);
  padding: 8px 12px;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tracking-wider {
  letter-spacing: 0.05em;
}

/* User Badge & RBAC Pill */
.user-badge {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 6px 4px 10px;
  background-color: var(--color-surface-card);
  border: 1px solid var(--color-surface-border);
  border-radius: 20px;
}

.user-avatar {
  width: 24px;
  height: 24px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
}

.username {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #ffffff;
}

.role-pill {
  font-size: 0.6875rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 2px 8px;
  border-radius: 12px;
}

.role-pill.admin {
  background: rgba(168, 85, 247, 0.2);
  color: #c084fc;
  border: 1px solid rgba(168, 85, 247, 0.4);
}

.role-pill.operator {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.4);
}

.role-pill.viewer {
  background: rgba(16, 185, 129, 0.2);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.4);
}

.btn-logout {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.btn-logout:hover {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}
</style>
