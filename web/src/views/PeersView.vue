<script setup lang="ts">
import { onMounted } from 'vue'
import { useBgpStore } from '../stores/bgpStore'
import StatusBadge from '../components/StatusBadge.vue'
import { RefreshCw, Network } from 'lucide-vue-next'

const bgpStore = useBgpStore()

onMounted(() => {
  bgpStore.fetchNeighbors()
  bgpStore.fetchStatus()
})
</script>

<template>
  <div class="peers-page">
    <div class="header-section">
      <div>
        <h1 class="page-title">BGP Peers & Neighbors</h1>
        <p class="page-subtitle">Real-time status of peering sessions, FSM states, and route prefix exchange counters.</p>
      </div>
      <button class="btn btn-secondary" @click="bgpStore.fetchNeighbors()" :disabled="bgpStore.loading">
        <RefreshCw :size="16" :class="{ 'animate-spin': bgpStore.loading }" /> Refresh Sessions
      </button>
    </div>

    <!-- Active Peers Card -->
    <div class="card">
      <div v-if="bgpStore.loading" class="loading-state">Querying BGP daemon for peers...</div>
      <div v-else-if="bgpStore.neighbors.length === 0" class="empty-state">
        <Network :size="48" class="empty-icon" />
        <p>No active BGP peering sessions discovered.</p>
      </div>
      <table v-else class="data-table">
        <thead>
          <tr>
            <th>Neighbor Address</th>
            <th>Remote AS</th>
            <th>Description</th>
            <th>FSM State</th>
            <th>Uptime</th>
            <th>Prefixes Recv</th>
            <th>Prefixes Accepted</th>
            <th>Prefixes Adv</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="peer in bgpStore.neighbors" :key="peer.neighbor_address">
            <td class="font-mono text-white font-medium">{{ peer.neighbor_address }}</td>
            <td class="font-mono">AS{{ peer.peer_as }}</td>
            <td class="text-muted">{{ peer.description || '—' }}</td>
            <td><StatusBadge :status="peer.state" /></td>
            <td class="font-mono text-sm">{{ peer.uptime || 'Active' }}</td>
            <td class="font-mono">{{ peer.prefixes_received ?? 0 }}</td>
            <td class="font-mono text-green">{{ peer.prefixes_accepted ?? 0 }}</td>
            <td class="font-mono text-blue">{{ peer.prefixes_advertised ?? 0 }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
.page-title {
  font-size: 1.75rem;
  font-weight: 700;
}
.page-subtitle {
  color: var(--color-text-muted);
  font-size: 0.875rem;
  margin-top: 4px;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}
.data-table th {
  text-align: left;
  padding: 12px;
  border-bottom: 1px solid var(--color-surface-border);
  color: var(--color-text-muted);
  font-size: 0.75rem;
  text-transform: uppercase;
}
.data-table td {
  padding: 14px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.text-green { color: #34d399; }
.text-blue { color: #60a5fa; }
.loading-state, .empty-state {
  padding: 48px;
  text-align: center;
  color: var(--color-text-muted);
}
.empty-icon {
  margin: 0 auto 12px;
  opacity: 0.4;
}
.animate-spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
