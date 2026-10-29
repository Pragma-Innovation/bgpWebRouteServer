<script setup lang="ts">
import { onMounted } from 'vue'
import { useBgpStore } from '../stores/bgpStore'
import { useFlowspecStore } from '../stores/flowspecStore'
import { usePrefixStore } from '../stores/prefixStore'
import { useRoutingStore } from '../stores/routingStore'
import StatusBadge from '../components/StatusBadge.vue'
import { Activity, ShieldAlert, Network, Server, ArrowRight, Database, Megaphone, ShieldBan } from 'lucide-vue-next'

const bgpStore = useBgpStore()
const flowspecStore = useFlowspecStore()
const prefixStore = usePrefixStore()
const routingStore = useRoutingStore()

onMounted(async () => {
  await Promise.all([
    bgpStore.fetchStatus(),
    bgpStore.fetchNeighbors(),
    flowspecStore.fetchRules(),
    prefixStore.fetchPrefixes(),
    routingStore.fetchAnnouncements(),
  ])
})
</script>

<template>
  <div class="dashboard-page">
    <div class="header-section">
      <div>
        <h1 class="page-title">Route Server Dashboard</h1>
        <p class="page-subtitle">Real-time overview of BGP sessions, multi-AFI routing, Flowspec rules, and RTBH mitigations.</p>
      </div>
      <div class="quick-status" v-if="bgpStore.status">
        <StatusBadge
          :status="bgpStore.status.ready ? 'online' : 'offline'"
          :label="bgpStore.status.ready ? 'Daemon Active' : 'Daemon Offline'"
        />
      </div>
    </div>

    <!-- Stat Grid -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon bg-blue">
          <ShieldAlert :size="24" />
        </div>
        <div class="stat-content">
          <span class="stat-label">Active Flowspec Rules</span>
          <span class="stat-value">{{ flowspecStore.rules.filter(r => r.is_active).length }}</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon bg-red">
          <ShieldBan :size="24" />
        </div>
        <div class="stat-content">
          <span class="stat-label">BGP Announcements (RTBH)</span>
          <span class="stat-value">{{ routingStore.announcements.filter(a => a.is_active).length }}</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon bg-cyan">
          <Database :size="24" />
        </div>
        <div class="stat-content">
          <span class="stat-label">Prefix Inventory</span>
          <span class="stat-value">{{ prefixStore.prefixes.length }}</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon bg-green">
          <Network :size="24" />
        </div>
        <div class="stat-content">
          <span class="stat-label">Established Peers</span>
          <span class="stat-value">
            {{ bgpStore.neighbors.filter(n => n.state === 'ESTABLISHED').length }}
            <span class="stat-total">/ {{ bgpStore.neighbors.length }}</span>
          </span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon bg-purple">
          <Server :size="24" />
        </div>
        <div class="stat-content">
          <span class="stat-label">Local AS Number</span>
          <span class="stat-value">AS{{ bgpStore.status?.as_number || '65000' }}</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon bg-amber">
          <Activity :size="24" />
        </div>
        <div class="stat-content">
          <span class="stat-label">BGP Backend Provider</span>
          <span class="stat-subtext">{{ bgpStore.status?.backend || 'MockBgpBackend' }}</span>
        </div>
      </div>
    </div>

    <!-- Main Content Grid -->
    <div class="grid-two-cols">
      <!-- Neighbors Snapshot -->
      <div class="card">
        <div class="card-header">
          <h2>Active BGP Neighbors</h2>
          <RouterLink to="/peers" class="btn btn-secondary text-sm">
            View All <ArrowRight :size="16" />
          </RouterLink>
        </div>
        <div v-if="bgpStore.loading" class="loading-state">Loading peers...</div>
        <div v-else-if="bgpStore.neighbors.length === 0" class="empty-state">No BGP neighbors configured yet.</div>
        <table v-else class="data-table">
          <thead>
            <tr>
              <th>Neighbor IP</th>
              <th>ASN</th>
              <th>Status</th>
              <th>Uptime</th>
              <th>Pfx (Recv/Adv)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="peer in bgpStore.neighbors" :key="peer.neighbor_address">
              <td class="font-mono">{{ peer.neighbor_address }}</td>
              <td class="font-mono">AS{{ peer.peer_as }}</td>
              <td><StatusBadge :status="peer.state" /></td>
              <td>{{ peer.uptime }}</td>
              <td class="font-mono">{{ peer.prefixes_received }} / {{ peer.prefixes_advertised }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Flowspec Rules Snapshot -->
      <div class="card">
        <div class="card-header">
          <h2>Recent Flowspec Rules</h2>
          <RouterLink to="/flowspec" class="btn btn-secondary text-sm">
            Manage Rules <ArrowRight :size="16" />
          </RouterLink>
        </div>
        <div v-if="flowspecStore.loading" class="loading-state">Loading rules...</div>
        <div v-else-if="flowspecStore.rules.length === 0" class="empty-state">No mitigation rules currently created.</div>
        <table v-else class="data-table">
          <thead>
            <tr>
              <th>Name / Target</th>
              <th>Family</th>
              <th>Action</th>
              <th>RIB Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="rule in flowspecStore.rules.slice(0, 5)" :key="rule.id">
              <td>
                <div class="font-medium">{{ rule.name || `Rule #${rule.id}` }}</div>
                <div class="text-xs text-muted font-mono">{{ rule.dst_prefix || 'Any Dest' }}</div>
              </td>
              <td><span class="badge badge-info">{{ rule.addr_fam }}</span></td>
              <td><span class="badge" :class="rule.action === 'Drop' ? 'badge-danger' : 'badge-warning'">{{ rule.action }}</span></td>
              <td><StatusBadge :status="rule.is_active ? 'active' : 'inactive'" :label="rule.is_active ? 'Injected' : 'Withdrawn'" /></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
}
.page-title {
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.page-subtitle {
  color: var(--color-text-muted);
  font-size: 0.875rem;
  margin-top: 4px;
}
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
  margin-bottom: 28px;
}
.stat-card {
  background-color: var(--color-surface);
  border: 1px solid var(--color-surface-border);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}
.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.bg-blue { background-color: rgba(59, 130, 246, 0.15); color: #60a5fa; }
.bg-green { background-color: rgba(16, 185, 129, 0.15); color: #34d399; }
.bg-purple { background-color: rgba(168, 85, 247, 0.15); color: #c084fc; }
.bg-amber { background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.bg-red { background-color: rgba(239, 68, 68, 0.15); color: #f87171; }
.bg-cyan { background-color: rgba(6, 182, 212, 0.15); color: #38bdf8; }
.stat-label {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--color-text-muted);
}
.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #ffffff;
}
.stat-total {
  font-size: 1rem;
  color: var(--color-text-dim);
  font-weight: 400;
}
.stat-subtext {
  font-size: 0.875rem;
  font-weight: 600;
  color: #e2e8f0;
}
.grid-two-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}
@media (max-width: 1024px) {
  .grid-two-cols {
    grid-template-columns: 1fr;
  }
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.card-header h2 {
  font-size: 1.125rem;
  font-weight: 600;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}
.data-table th {
  text-align: left;
  padding: 10px 12px;
  border-bottom: 1px solid var(--color-surface-border);
  color: var(--color-text-muted);
  font-weight: 500;
  font-size: 0.75rem;
  text-transform: uppercase;
}
.data-table td {
  padding: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.loading-state, .empty-state {
  padding: 32px;
  text-align: center;
  color: var(--color-text-muted);
  font-size: 0.875rem;
}
.text-muted { color: var(--color-text-muted); }
.text-xs { font-size: 0.75rem; }
.font-medium { font-weight: 500; }
</style>
