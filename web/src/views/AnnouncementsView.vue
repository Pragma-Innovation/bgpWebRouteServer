<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoutingStore, type BgpAnnouncement } from '../stores/routingStore'
import { useAuthStore } from '../stores/authStore'
import { RefreshCw, Search, Filter, ShieldAlert, Database, Layers, CheckCircle2, AlertCircle, Send, X } from 'lucide-vue-next'

const routingStore = useRoutingStore()
const authStore = useAuthStore()

// Filter state
const selectedPseudoRib = ref<string>('ALL')
const selectedAfi = ref<string>('ALL')
const selectedStatus = ref<string>('ALL')
const selectedAction = ref<string>('ALL')
const searchDst = ref('')
const searchProto = ref('')
const searchPort = ref('')
const searchQuery = ref('')

onMounted(async () => {
  await routingStore.fetchRibs()
  await routingStore.fetchPseudoRibs()
  await routingStore.fetchAnnouncements()
})

const filteredAnnouncements = computed(() => {
  return routingStore.announcements.filter(ann => {
    // Pseudo-RIB filter
    if (selectedPseudoRib.value !== 'ALL' && ann.pseudo_rib.toString() !== selectedPseudoRib.value) {
      return false
    }

    // AFI/SAFI filter
    if (selectedAfi.value !== 'ALL' && ann.afi_safi !== selectedAfi.value) {
      return false
    }

    // Status filter
    if (selectedStatus.value !== 'ALL' && ann.status !== selectedStatus.value) {
      return false
    }

    // Action filter
    if (selectedAction.value !== 'ALL' && ann.action !== selectedAction.value) {
      return false
    }

    // Search destination
    if (searchDst.value) {
      const q = searchDst.value.toLowerCase()
      const matchPrefix = ann.prefix_cidr && ann.prefix_cidr.toLowerCase().includes(q)
      const matchFsDst = ann.flowspec_tuple?.dst_prefix && ann.flowspec_tuple.dst_prefix.toLowerCase().includes(q)
      const matchRepr = ann.route_repr && ann.route_repr.toLowerCase().includes(q)
      if (!matchPrefix && !matchFsDst && !matchRepr) return false
    }

    // Protocol filter
    if (searchProto.value) {
      if (!ann.flowspec_tuple || !ann.flowspec_tuple.proto_number) return false
      if (!ann.flowspec_tuple.proto_number.includes(searchProto.value)) return false
    }

    // Port filter
    if (searchPort.value) {
      if (!ann.flowspec_tuple) return false
      const matchPort = (ann.flowspec_tuple.dst_port && ann.flowspec_tuple.dst_port.includes(searchPort.value)) ||
                        (ann.flowspec_tuple.src_port && ann.flowspec_tuple.src_port.includes(searchPort.value)) ||
                        (ann.flowspec_tuple.port && ann.flowspec_tuple.port.includes(searchPort.value))
      if (!matchPort) return false
    }

    // General search query
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      const matchGeneral = ann.route_repr.toLowerCase().includes(q) ||
                           ann.pseudo_rib_name.toLowerCase().includes(q) ||
                           (ann.next_hop && ann.next_hop.includes(q))
      if (!matchGeneral) return false
    }

    return true
  })
})

function resetFilters() {
  selectedPseudoRib.value = 'ALL'
  selectedAfi.value = 'ALL'
  selectedStatus.value = 'ALL'
  selectedAction.value = 'ALL'
  searchDst.value = ''
  searchProto.value = ''
  searchPort.value = ''
  searchQuery.value = ''
}

async function handlePushRib() {
  if (!routingStore.activeRib) return
  try {
    const res = await routingStore.pushRibToBgp(routingStore.activeRib.id)
    alert(`Pushed ${res.pushed_count} routes into GoBGP Loc-RIB successfully!`)
  } catch (err: any) {
    alert(err.message || 'Push failed')
  }
}

function formatDate(isoStr: string | null) {
  if (!isoStr) return 'Never'
  const d = new Date(isoStr)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
</script>

<template>
  <div class="announcements-page">
    <!-- Header -->
    <div class="header-section">
      <div>
        <h1 class="page-title">GoBGP Global Loc-RIB Announcements</h1>
        <p class="page-subtitle">Real-time inspection of all routes programmed into GoBGP across IPv4/IPv6 Unicast and Flowspec.</p>
      </div>
      <div class="header-actions">
        <button
          v-if="routingStore.activeRib"
          class="btn btn-push"
          :disabled="!authStore.canEdit || routingStore.pushingRib"
          @click="handlePushRib"
        >
          <Send :size="18" />
          {{ routingStore.pushingRib ? 'Synchronizing...' : `Push '${routingStore.activeRib.name}' to GoBGP` }}
        </button>
        <button class="btn btn-secondary" @click="routingStore.fetchAnnouncements()">
          <RefreshCw :size="16" :class="{ 'spin': routingStore.loadingAnnouncements }" /> Refresh
        </button>
      </div>
    </div>

    <!-- Active RIB Sync Bar -->
    <div v-if="routingStore.activeRib" class="card sync-banner">
      <div class="flex items-center gap-2">
        <Layers :size="18" class="text-primary" />
        <span class="text-xs text-muted">Target BGP Speaker:</span>
        <span class="font-bold text-white text-xs">GoBGP (10.100.0.10, AS65000)</span>
        <span class="text-xs text-muted ml-2">Active RIB:</span>
        <span class="badge badge-blue text-xs">{{ routingStore.activeRib.name }}</span>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-xs text-muted">State:</span>
        <span class="badge" :class="routingStore.activeRib.status === 'SYNCED' ? 'badge-green' : 'badge-amber'">
          {{ routingStore.activeRib.status }}
        </span>
        <span class="text-xs text-muted">Last push: {{ routingStore.activeRib.last_pushed_at ? new Date(routingStore.activeRib.last_pushed_at).toLocaleTimeString() : 'Never' }}</span>
      </div>
    </div>

    <!-- Multi-facet Filters Bar -->
    <div class="card filters-container">
      <div class="filters-row">
        <!-- Pseudo-RIB Selector -->
        <div class="filter-item">
          <label class="filter-label">Pseudo-RIB Container:</label>
          <select v-model="selectedPseudoRib" class="select-input">
            <option value="ALL">All Pseudo-RIBs</option>
            <option v-for="pr in routingStore.pseudoRibs" :key="pr.id" :value="pr.id.toString()">
              {{ pr.name }} ({{ pr.afi_safi }})
            </option>
          </select>
        </div>

        <!-- AFI/SAFI Selector -->
        <div class="filter-item">
          <label class="filter-label">Address Family (AFI/SAFI):</label>
          <select v-model="selectedAfi" class="select-input">
            <option value="ALL">All AFI/SAFIs</option>
            <option value="ipv4-unicast">IPv4 Unicast (AFI 1, SAFI 1)</option>
            <option value="ipv6-unicast">IPv6 Unicast (AFI 2, SAFI 1)</option>
            <option value="ipv4-flowspec">IPv4 Flowspec (AFI 1, SAFI 133)</option>
            <option value="ipv6-flowspec">IPv6 Flowspec (AFI 2, SAFI 133)</option>
          </select>
        </div>

        <!-- Status Selector -->
        <div class="filter-item">
          <label class="filter-label">BGP State:</label>
          <select v-model="selectedStatus" class="select-input">
            <option value="ALL">All States</option>
            <option value="ACTIVE">Active (In GoBGP)</option>
            <option value="WITHDRAWN">Withdrawn</option>
            <option value="ERROR">Sync Error</option>
          </select>
        </div>

        <!-- Action Selector -->
        <div class="filter-item">
          <label class="filter-label">Flowspec Action:</label>
          <select v-model="selectedAction" class="select-input">
            <option value="ALL">All Actions</option>
            <option value="Drop">Drop</option>
            <option value="Shape">Shape</option>
            <option value="Redirect">Redirect</option>
            <option value="Mark">Mark</option>
          </select>
        </div>
      </div>

      <!-- Flowspec Tuple & Text Search Sub-Row -->
      <div class="filters-row mt-3 pt-3 border-top">
        <div class="filter-input-wrap flex-1">
          <Search :size="14" class="input-icon" />
          <input
            v-model="searchDst"
            type="text"
            class="search-input-sm"
            placeholder="Filter by Destination IP / Prefix..."
          />
        </div>
        <div class="filter-input-wrap w-36">
          <input
            v-model="searchProto"
            type="text"
            class="search-input-sm"
            placeholder="Protocol (e.g. 6)..."
          />
        </div>
        <div class="filter-input-wrap w-36">
          <input
            v-model="searchPort"
            type="text"
            class="search-input-sm"
            placeholder="Port (e.g. 22)..."
          />
        </div>
        <div class="filter-input-wrap flex-1">
          <input
            v-model="searchQuery"
            type="text"
            class="search-input-sm"
            placeholder="Free text search..."
          />
        </div>
        <button class="btn-reset-filters" @click="resetFilters" title="Reset all filters">
          <X :size="14" /> Reset
        </button>
      </div>

      <div class="results-stats mt-2">
        Showing <strong>{{ filteredAnnouncements.length }}</strong> of <strong>{{ routingStore.announcements.length }}</strong> routes in GoBGP Loc-RIB
      </div>
    </div>

    <!-- Live Loc-RIB Table -->
    <div class="card table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>Route / Flowspec NLRI</th>
            <th>Family (AFI/SAFI)</th>
            <th>Origin Pseudo-RIB</th>
            <th>BGP Path Attributes</th>
            <th>GoBGP State</th>
            <th>Last Synced</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="filteredAnnouncements.length === 0">
            <td colspan="6" class="text-center empty-state">
              No matching routes found in GoBGP Loc-RIB. Check your filter settings or push a Master RIB.
            </td>
          </tr>
          <tr v-for="ann in filteredAnnouncements" :key="ann.id">
            <!-- Route / NLRI details -->
            <td>
              <!-- Unicast Presentation -->
              <div v-if="!ann.afi_safi.includes('flowspec')" class="flex items-center gap-2">
                <Database :size="16" class="text-blue flex-shrink-0" />
                <div>
                  <div class="font-mono text-bold text-accent text-sm">{{ ann.route_repr }}</div>
                  <div class="text-xs text-muted">Unicast Prefix</div>
                </div>
              </div>

              <!-- Flowspec Tuple Presentation -->
              <div v-else class="fs-tuple-cell">
                <div class="flex items-center gap-2 mb-1">
                  <ShieldAlert :size="16" class="text-amber flex-shrink-0" />
                  <span class="font-bold text-white text-xs">{{ ann.flowspec_tuple?.name || 'Flowspec Match' }}</span>
                  <span
                    class="badge"
                    :class="ann.action === 'Drop' ? 'badge-danger' : 'badge-warning'"
                  >
                    {{ ann.action || 'Drop' }}
                  </span>
                </div>
                <div class="fs-chips">
                  <span class="fs-chip">dst: {{ ann.flowspec_tuple?.dst_prefix || 'any' }}</span>
                  <span v-if="ann.flowspec_tuple?.src_prefix" class="fs-chip">src: {{ ann.flowspec_tuple.src_prefix }}</span>
                  <span v-if="ann.flowspec_tuple?.proto_number" class="fs-chip">proto: {{ ann.flowspec_tuple.proto_number === '6' ? 'TCP (6)' : ann.flowspec_tuple.proto_number }}</span>
                  <span v-if="ann.flowspec_tuple?.dst_port" class="fs-chip">dport: {{ ann.flowspec_tuple.dst_port }}</span>
                </div>
              </div>
            </td>

            <!-- Family -->
            <td>
              <span
                class="badge"
                :class="ann.afi_safi.includes('flowspec') ? 'badge-amber' : (ann.afi_safi.includes('ipv4') ? 'badge-blue' : 'badge-purple')"
              >
                {{ ann.afi_safi }}
              </span>
            </td>

            <!-- Origin Pseudo-RIB -->
            <td>
              <div class="font-semibold text-white text-xs">{{ ann.pseudo_rib_name }}</div>
              <div v-if="ann.rib_name" class="text-xs text-muted">via {{ ann.rib_name }}</div>
            </td>

            <!-- Path Attributes -->
            <td>
              <div v-if="ann.next_hop" class="text-xs font-mono text-white mb-1">
                NH: {{ ann.next_hop }}
              </div>
              <div class="community-tags">
                <span v-for="c in ann.communities" :key="c" class="tag-pill font-mono text-xs">
                  {{ c }}
                </span>
                <span v-for="lc in ann.large_communities" :key="lc" class="tag-pill tag-large font-mono text-xs">
                  {{ lc }}
                </span>
                <span v-if="(!ann.communities || ann.communities.length === 0) && (!ann.large_communities || ann.large_communities.length === 0)" class="text-xs text-muted">
                  —
                </span>
              </div>
            </td>

            <!-- GoBGP State -->
            <td>
              <div class="flex items-center gap-2">
                <span
                  class="status-pill"
                  :class="{
                    'status-active': ann.status === 'ACTIVE',
                    'status-withdrawn': ann.status === 'WITHDRAWN',
                    'status-error': ann.status === 'ERROR',
                  }"
                >
                  <span class="status-dot"></span>
                  {{ ann.status }}
                </span>
                <span
                  v-if="ann.programmed_in_rib"
                  class="badge badge-green text-xs"
                  title="Confirmed in GoBGP Global Loc-RIB"
                >
                  In Loc-RIB
                </span>
              </div>
              <div v-if="ann.error_message" class="text-xs text-danger mt-1">
                {{ ann.error_message }}
              </div>
            </td>

            <!-- Last Synced -->
            <td class="text-xs text-muted font-mono">
              {{ formatDate(ann.last_synced_at) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.announcements-page {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #fff;
  margin: 0;
}

.page-subtitle {
  font-size: 0.875rem;
  color: #94a3b8;
  margin: 0.25rem 0 0 0;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
}

.btn-push {
  background: #10b981;
  color: #fff;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  border: none;
  cursor: pointer;
}

.btn-push:hover:not(:disabled) {
  background: #059669;
}

.sync-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1.25rem;
  background: #0f172a;
  border: 1px solid #334155;
}

/* Filters */
.filters-container {
  padding: 1rem 1.25rem;
}

.filters-row {
  display: flex;
  gap: 1rem;
  align-items: center;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.filter-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
}

.select-input {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 0.45rem 0.65rem;
  color: #f8fafc;
  font-size: 0.85rem;
}

.filter-input-wrap {
  position: relative;
}

.input-icon {
  position: absolute;
  left: 0.65rem;
  top: 50%;
  transform: translateY(-50%);
  color: #64748b;
}

.search-input-sm {
  width: 100%;
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 0.4rem 0.65rem 0.4rem 2rem;
  color: #f8fafc;
  font-size: 0.8rem;
}

.btn-reset-filters {
  background: none;
  border: 1px solid #475569;
  color: #cbd5e1;
  padding: 0.4rem 0.65rem;
  border-radius: 6px;
  font-size: 0.8rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.btn-reset-filters:hover {
  border-color: #94a3b8;
  color: #fff;
}

.results-stats {
  font-size: 0.8rem;
  color: #64748b;
}

.border-top {
  border-top: 1px solid #1e293b;
}

/* Table */
.table-container {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 0.875rem;
}

.data-table th {
  padding: 0.75rem 1rem;
  color: #94a3b8;
  font-weight: 600;
  border-bottom: 1px solid #334155;
}

.data-table td {
  padding: 0.85rem 1rem;
  border-bottom: 1px solid #1e293b;
}

.empty-state {
  padding: 3rem;
  color: #64748b;
}

.fs-tuple-cell {
  display: flex;
  flex-direction: column;
}

.fs-chips {
  display: flex;
  gap: 0.3rem;
  flex-wrap: wrap;
}

.fs-chip {
  font-family: monospace;
  font-size: 0.75rem;
  background: #1e293b;
  color: #cbd5e1;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
}

.community-tags {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.tag-pill {
  font-size: 0.75rem;
  background: #1e293b;
  color: #38bdf8;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
}

.tag-large {
  color: #c084fc;
}

.badge {
  display: inline-block;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.badge-blue { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
.badge-purple { background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }
.badge-amber { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
.badge-green { background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); }
.badge-danger { background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
.badge-warning { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.2rem 0.6rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.status-dot { width: 6px; height: 6px; border-radius: 50%; }
.status-active { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.status-active .status-dot { background: #22c55e; }
.status-withdrawn { background: rgba(234, 179, 8, 0.15); color: #facc15; }
.status-withdrawn .status-dot { background: #eab308; }
.status-error { background: rgba(239, 68, 68, 0.15); color: #f87171; }
.status-error .status-dot { background: #ef4444; }

.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
