<script setup lang="ts">
import { onMounted } from 'vue'
import { useBgpStore } from '../stores/bgpStore'
import StatusBadge from '../components/StatusBadge.vue'
import { Server, Database, Shield, Radio } from 'lucide-vue-next'

const bgpStore = useBgpStore()

onMounted(() => {
  bgpStore.fetchStatus()
})
</script>

<template>
  <div class="settings-page">
    <div class="header-section">
      <div>
        <h1 class="page-title">System & BGP Architecture</h1>
        <p class="page-subtitle">Inspect the active BGP backend driver, API connections, and cloud-native runtime.</p>
      </div>
    </div>

    <div class="settings-grid">
      <!-- Active BGP Stack Card -->
      <div class="card">
        <div class="card-icon bg-blue">
          <Server :size="24" />
        </div>
        <h2>Active BGP Engine Provider</h2>
        <p class="card-desc">
          Current driver resolved by <code>BgpManager</code> according to the Strategy/Provider pattern.
        </p>

        <div class="info-list">
          <div class="info-row">
            <span class="info-key">Provider Driver</span>
            <span class="info-val font-mono text-white">{{ bgpStore.status?.backend || 'Loading...' }}</span>
          </div>
          <div class="info-row">
            <span class="info-key">Daemon Readiness</span>
            <span class="info-val">
              <StatusBadge :status="bgpStore.status?.ready ? 'online' : 'warning'" :label="bgpStore.status?.ready ? 'Operational' : 'Degraded'" />
            </span>
          </div>
          <div class="info-row">
            <span class="info-key">Local Router ID</span>
            <span class="info-val font-mono">{{ bgpStore.status?.router_id || '10.0.0.1' }}</span>
          </div>
          <div class="info-row">
            <span class="info-key">Local ASN</span>
            <span class="info-val font-mono">AS{{ bgpStore.status?.as_number || 65000 }}</span>
          </div>
        </div>
      </div>

      <!-- Pluggable Stack Roadmap Card -->
      <div class="card">
        <div class="card-icon bg-purple">
          <Radio :size="24" />
        </div>
        <h2>Multi-Stack Extensibility</h2>
        <p class="card-desc">
          Architecture designed to support multiple open-source BGP stacks via <code>BaseBgpBackend</code>.
        </p>

        <div class="stack-list">
          <div class="stack-item active">
            <span class="font-medium">GoBGP</span>
            <span class="badge badge-success">Reference Stack</span>
          </div>
          <div class="stack-item active">
            <span class="font-medium">Mock BGP Driver</span>
            <span class="badge badge-info">Dev & CI Mode</span>
          </div>
          <div class="stack-item future">
            <span class="font-medium">BIRD</span>
            <span class="badge badge-warning">Future Release</span>
          </div>
          <div class="stack-item future">
            <span class="font-medium">FRRouting (FRR)</span>
            <span class="badge badge-warning">Future Release</span>
          </div>
          <div class="stack-item future">
            <span class="font-medium">ExaBGP</span>
            <span class="badge badge-warning">Future Release</span>
          </div>
        </div>
      </div>

      <!-- Database & Persistence Card -->
      <div class="card">
        <div class="card-icon bg-green">
          <Database :size="24" />
        </div>
        <h2>Data Persistence & ORM</h2>
        <p class="card-desc">
          Relational storage layer replacing legacy flat <code>.fslib</code> text files.
        </p>
        <div class="info-list">
          <div class="info-row">
            <span class="info-key">Database Engine</span>
            <span class="info-val">PostgreSQL 16 (with SQLite dev fallback)</span>
          </div>
          <div class="info-row">
            <span class="info-key">Backend Framework</span>
            <span class="info-val">Django 5.2 LTS + Django REST Framework</span>
          </div>
          <div class="info-row">
            <span class="info-key">Frontend Framework</span>
            <span class="info-val">Vue 3 + Vite + TypeScript + Pinia</span>
          </div>
        </div>
      </div>

      <!-- Cloud-Native & Kubernetes Card -->
      <div class="card">
        <div class="card-icon bg-amber">
          <Shield :size="24" />
        </div>
        <h2>Kubernetes Runtime Health</h2>
        <p class="card-desc">
          Cloud-native probes exposed for orchestrator liveness and readiness monitoring.
        </p>
        <div class="info-list">
          <div class="info-row">
            <span class="info-key">Liveness Probe</span>
            <span class="info-val font-mono text-xs">/api/health/live/</span>
          </div>
          <div class="info-row">
            <span class="info-key">Readiness Probe</span>
            <span class="info-val font-mono text-xs">/api/health/ready/</span>
          </div>
          <div class="info-row">
            <span class="info-key">BGP Port 179</span>
            <span class="info-val">hostNetwork / LoadBalancer enabled</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-title {
  font-size: 1.75rem;
  font-weight: 700;
  margin-bottom: 4px;
}
.page-subtitle {
  color: var(--color-text-muted);
  font-size: 0.875rem;
  margin-bottom: 28px;
}
.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 24px;
}
.card-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}
.bg-blue { background-color: rgba(59, 130, 246, 0.15); color: #60a5fa; }
.bg-purple { background-color: rgba(168, 85, 247, 0.15); color: #c084fc; }
.bg-green { background-color: rgba(16, 185, 129, 0.15); color: #34d399; }
.bg-amber { background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.card h2 {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 6px;
}
.card-desc {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  margin-bottom: 20px;
}
.info-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.875rem;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.info-key {
  color: var(--color-text-muted);
}
.info-val {
  font-weight: 500;
}
.stack-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.stack-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-radius: 6px;
  background-color: rgba(255, 255, 255, 0.03);
  font-size: 0.875rem;
}
.stack-item.active {
  border-left: 3px solid #3b82f6;
}
.stack-item.future {
  border-left: 3px solid #64748b;
  opacity: 0.7;
}
</style>
