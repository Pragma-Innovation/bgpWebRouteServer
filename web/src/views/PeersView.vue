<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  useBgpStore,
  type BgpPeerConfig,
  type BgpUnifiedSession,
} from '../stores/bgpStore'
import { useAuthStore } from '../stores/authStore'
import StatusBadge from '../components/StatusBadge.vue'
import GlobalConfigModal from '../components/GlobalConfigModal.vue'
import PeerModal from '../components/PeerModal.vue'
import {
  RefreshCw,
  Network,
  Server,
  Plus,
  Sliders,
  RotateCcw,
  Pencil,
  Trash2,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Radio,
  Search,
  Check,
  Layers,
  Activity,
  ArrowDownToLine,
  Flame,
} from 'lucide-vue-next'

const bgpStore = useBgpStore()
const authStore = useAuthStore()

// State
const isRefreshing = ref(false)
const selectedPeerAddress = ref<string | null>(null)
const showGlobalModal = ref(false)
const showPeerModal = ref(false)
const peerToEdit = ref<BgpPeerConfig | null>(null)
const actionFeedback = ref<{ type: 'success' | 'error'; message: string } | null>(null)

// Filtering & Search
type FilterTab = 'all' | 'managed' | 'discovered' | 'established'
const activeTab = ref<FilterTab>('all')
const searchQuery = ref('')

// Background continuous synchronization polling (5s interval)
let autoSyncTimer: any = null

async function silentSync() {
  if (isRefreshing.value || bgpStore.reconciling || bgpStore.savingPeer) return
  try {
    await bgpStore.fetchSessions()
    await bgpStore.fetchStatus()
  } catch {
    // Silent fail for polling
  }
}

async function refreshAll() {
  isRefreshing.value = true
  try {
    await Promise.allSettled([
      bgpStore.fetchGlobalConfig(),
      bgpStore.fetchSessions(),
      bgpStore.fetchStatus(),
    ])
  } finally {
    isRefreshing.value = false
  }
}

onMounted(async () => {
  await refreshAll()
  autoSyncTimer = setInterval(silentSync, 5000)
})

onUnmounted(() => {
  if (autoSyncTimer) {
    clearInterval(autoSyncTimer)
    autoSyncTimer = null
  }
})

// Metrics computed
const totalCount = computed(() => bgpStore.sessions.length)
const managedCount = computed(() => bgpStore.sessions.filter((s) => s.is_managed).length)
const discoveredCount = computed(() => bgpStore.sessions.filter((s) => !s.is_managed).length)
const establishedCount = computed(
  () => bgpStore.sessions.filter((s) => s.state === 'ESTABLISHED').length
)

// Filtered list
const filteredSessions = computed(() => {
  let list = bgpStore.sessions || []

  if (activeTab.value === 'managed') {
    list = list.filter((s) => s.is_managed)
  } else if (activeTab.value === 'discovered') {
    list = list.filter((s) => !s.is_managed)
  } else if (activeTab.value === 'established') {
    list = list.filter((s) => s.state === 'ESTABLISHED')
  }

  const q = searchQuery.value.trim().toLowerCase()
  if (q) {
    list = list.filter((s) => {
      const addr = (s.neighbor_address || '').toLowerCase()
      const asNum = String(s.peer_as || '')
      const desc = (s.description || '').toLowerCase()
      return addr.includes(q) || asNum.includes(q) || desc.includes(q)
    })
  }

  return list
})

function selectPeer(addr?: string) {
  if (!addr) return
  const cleanAddr = addr.trim().toLowerCase()
  const current = (selectedPeerAddress.value || '').trim().toLowerCase()
  selectedPeerAddress.value = current === cleanAddr ? null : addr
}

const selectedSession = computed(() => {
  if (!selectedPeerAddress.value) return null
  const target = selectedPeerAddress.value.trim().toLowerCase()
  return (
    bgpStore.sessions.find(
      (s) => (s.neighbor_address || '').trim().toLowerCase() === target
    ) || null
  )
})

function openAddPeerModal() {
  peerToEdit.value = null
  showPeerModal.value = true
}

function openEditPeerModal(session: BgpUnifiedSession) {
  if (!session.config) return
  peerToEdit.value = session.config
  showPeerModal.value = true
}

function openAdoptPeerModal(session: BgpUnifiedSession) {
  peerToEdit.value = {
    neighbor_address: session.neighbor_address || '',
    peer_as: session.peer_as || 65001,
    description: session.description || 'Adopted BGP neighbor',
    is_enabled: true,
    multihop_enabled: session.session_type === 'eBGP',
    multihop_ttl: 64,
    passive_mode: false,
    hold_time: 90,
    keepalive_interval: 30,
    families: ['ipv4-unicast', 'ipv4-flowspec'],
  }
  showPeerModal.value = true
}

async function handleReconcile() {
  actionFeedback.value = null
  try {
    const res = await bgpStore.reconcilePeers()
    const pushedStr =
      res.pushed_to_gobgp.length > 0
        ? ` (Pushed: ${res.pushed_to_gobgp.join(', ')})`
        : ''
    actionFeedback.value = {
      type: 'success',
      message: `Reconciliation synchronized ${res.total_sessions} total sessions: ${res.managed_count} managed, ${res.discovered_count} discovered unmanaged.${pushedStr}`,
    }
  } catch (err: any) {
    actionFeedback.value = {
      type: 'error',
      message: err.message || 'Failed to reconcile peering sessions',
    }
  }
}

async function handleResetPeer(session: BgpUnifiedSession, soft: boolean = true) {
  if (!session.config?.id) return
  if (
    !confirm(
      `Are you sure you want to send a ${
        soft ? 'Soft Reset (Route Refresh)' : 'Hard Reset (Session Teardown)'
      } to ${session.neighbor_address}?`
    )
  ) {
    return
  }
  actionFeedback.value = null
  try {
    const res = await bgpStore.resetPeer(session.config.id, soft)
    actionFeedback.value = { type: 'success', message: res.detail }
  } catch (err: any) {
    actionFeedback.value = {
      type: 'error',
      message: err.message || 'Failed to reset session',
    }
  }
}

async function handleDeletePeer(session: BgpUnifiedSession) {
  if (!session.config?.id) return
  if (
    !confirm(
      `Are you sure you want to remove peering session ${session.neighbor_address} (AS${session.peer_as})? This will teardown the live BGP session.`
    )
  ) {
    return
  }
  actionFeedback.value = null
  try {
    await bgpStore.deletePeerConfig(session.config.id)
    if (selectedPeerAddress.value === session.neighbor_address) {
      selectedPeerAddress.value = null
    }
    actionFeedback.value = {
      type: 'success',
      message: `Peer ${session.neighbor_address} removed from configuration and GoBGP stack.`,
    }
  } catch (err: any) {
    actionFeedback.value = {
      type: 'error',
      message: err.message || 'Failed to delete peer',
    }
  }
}

function formatUptime(seconds?: string | number): string {
  if (!seconds || seconds === 0 || seconds === '—') return '—'
  const sec = Number(seconds)
  if (isNaN(sec) || sec <= 0) return '—'
  if (sec > 1000000000) {
    const now = Math.floor(Date.now() / 1000)
    const diff = Math.max(0, now - sec)
    if (diff < 60) return `${diff}s`
    if (diff < 3600) return `${Math.floor(diff / 60)}m ${diff % 60}s`
    return `${Math.floor(diff / 3600)}h ${Math.floor((diff % 3600) / 60)}m`
  }
  if (sec < 60) return `${sec}s`
  if (sec < 3600) return `${Math.floor(sec / 60)}m ${sec % 60}s`
  return `${Math.floor(sec / 3600)}h ${Math.floor((sec % 3600) / 60)}m`
}
</script>

<template>
  <div class="peers-page">
    <!-- Header Section -->
    <div class="header-section">
      <div>
        <h1 class="page-title">BGP Peers & Backbone Sessions</h1>
        <p class="page-subtitle">
          Unified control plane: continuous synchronization between Gabu database intent and GoBGP runtime.
        </p>
      </div>
      <div class="action-buttons">
        <!-- Live continuous synchronization badge -->
        <div class="live-sync-indicator" title="Continuous background synchronization active (5s interval)">
          <span class="pulse-dot"></span>
          <span class="sync-text">Continuous Sync</span>
        </div>

        <button
          v-if="authStore.isAdmin"
          class="btn btn-secondary"
          @click="handleReconcile"
          :disabled="bgpStore.reconciling"
          title="Run active reconciliation: push DB intent to GoBGP and align states"
        >
          <RotateCcw :size="16" :class="{ 'animate-spin': bgpStore.reconciling }" />
          <span>{{ bgpStore.reconciling ? 'Reconciling...' : 'Reconcile Now' }}</span>
        </button>

        <button
          v-if="authStore.isAdmin"
          class="btn btn-primary"
          @click="openAddPeerModal"
        >
          <Plus :size="16" />
          <span>Add BGP Neighbor</span>
        </button>

        <button class="btn btn-secondary" @click="refreshAll" :disabled="isRefreshing">
          <RefreshCw :size="16" :class="{ 'animate-spin': isRefreshing }" />
          <span>{{ isRefreshing ? 'Refreshing...' : 'Refresh' }}</span>
        </button>
      </div>
    </div>

    <!-- Alert / Feedback Banner -->
    <div v-if="actionFeedback" class="alert-banner" :class="actionFeedback.type">
      <CheckCircle2 v-if="actionFeedback.type === 'success'" :size="18" />
      <AlertCircle v-else :size="18" />
      <span>{{ actionFeedback.message }}</span>
      <button class="banner-close" @click="actionFeedback = null">✕</button>
    </div>

    <!-- Role Notice Banner if not admin -->
    <div v-if="!authStore.isAdmin" class="alert-banner info">
      <ShieldCheck :size="18" class="text-blue" />
      <span>
        Operating in <strong>{{ authStore.role }}</strong> mode (Read-Only). Administrator privileges are required to configure router settings, add/edit BGP neighbors, or adopt discovered sessions.
      </span>
    </div>

    <!-- Global Router Parameters Header Card -->
    <div class="card router-card">
      <div class="router-header">
        <div class="router-identity">
          <div class="router-avatar">
            <Server :size="24" class="text-primary" />
          </div>
          <div>
            <div class="router-title-wrap">
              <h2 class="router-name">Local BGP Speaker</h2>
              <span class="badge badge-info">GoBGP Backend</span>
            </div>
            <div class="router-sub font-mono">
              Router ID: <span class="text-white">{{ bgpStore.globalConfig?.router_id || '10.100.0.10' }}</span>
            </div>
          </div>
        </div>

        <div class="router-metrics">
          <div class="metric-box">
            <div class="metric-label">Local ASN</div>
            <div class="metric-value font-mono text-primary">
              AS{{ bgpStore.globalConfig?.local_as || 65000 }}
            </div>
          </div>

          <div class="metric-box">
            <div class="metric-label">Listening Port</div>
            <div class="metric-value font-mono">
              TCP {{ bgpStore.globalConfig?.listen_port || 179 }}
            </div>
          </div>

          <div class="metric-box">
            <div class="metric-label">Active Sessions</div>
            <div class="metric-value font-mono">
              <span class="text-green">{{ establishedCount }}</span> / {{ totalCount }} established
            </div>
          </div>

          <div class="metric-box">
            <div class="metric-label">Managed / Discovered</div>
            <div class="metric-value font-mono">
              <span class="text-blue">{{ managedCount }}</span> / <span class="text-warning">{{ discoveredCount }}</span>
            </div>
          </div>

          <button
            v-if="authStore.isAdmin"
            class="btn btn-secondary configure-btn"
            @click="showGlobalModal = true"
            title="Configure Local BGP ASN, Router ID, and Port"
          >
            <Sliders :size="16" />
            <span>Configure Router</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Unified Peering Sessions Card (Single Table View) -->
    <div class="card">
      <div class="card-toolbar">
        <div>
          <h3 class="card-title">Peering Sessions</h3>
          <p class="card-subtitle">
            Consolidated single view of database-managed configurations and live runtime-discovered BGP sessions.
          </p>
        </div>

        <!-- Filter Tabs & Search Controls -->
        <div class="toolbar-controls">
          <!-- Filter Tabs -->
          <div class="filter-tabs">
            <button
              class="tab-btn"
              :class="{ 'tab-active': activeTab === 'all' }"
              @click="activeTab = 'all'"
            >
              All Sessions
              <span class="tab-badge">{{ totalCount }}</span>
            </button>
            <button
              class="tab-btn"
              :class="{ 'tab-active': activeTab === 'managed' }"
              @click="activeTab = 'managed'"
            >
              Managed
              <span class="tab-badge badge-blue">{{ managedCount }}</span>
            </button>
            <button
              class="tab-btn"
              :class="{ 'tab-active': activeTab === 'discovered' }"
              @click="activeTab = 'discovered'"
            >
              Discovered
              <span class="tab-badge" :class="discoveredCount > 0 ? 'badge-amber' : ''">{{ discoveredCount }}</span>
            </button>
            <button
              class="tab-btn"
              :class="{ 'tab-active': activeTab === 'established' }"
              @click="activeTab = 'established'"
            >
              Established
              <span class="tab-badge badge-green">{{ establishedCount }}</span>
            </button>
          </div>

          <!-- Search input -->
          <div class="search-box">
            <Search :size="15" class="search-icon" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Filter by IP, ASN, name..."
              class="search-input"
            />
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="bgpStore.loadingSessions && bgpStore.sessions.length === 0" class="loading-state">
        <RotateCcw :size="24" class="animate-spin mb-2" />
        <p>Loading unified peering sessions...</p>
      </div>

      <!-- Empty State -->
      <div v-else-if="filteredSessions.length === 0" class="empty-state">
        <Network :size="48" class="empty-icon" />
        <p class="text-lg font-medium text-white">No peering sessions match the criteria</p>
        <p class="text-sm text-muted mt-1">
          {{ searchQuery ? 'Try adjusting your search query or switching tabs.' : 'Configure your first BGP neighbor or connect backbone routers.' }}
        </p>
        <button
          v-if="authStore.isAdmin && totalCount === 0"
          class="btn btn-primary mt-4"
          @click="openAddPeerModal"
        >
          <Plus :size="16" />
          <span>Add Your First Neighbor</span>
        </button>
      </div>

      <!-- Unified Data Table -->
      <div v-else class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>Neighbor Address</th>
              <th>Origin & Sync</th>
              <th>Type / ASN</th>
              <th>Capabilities / Flags</th>
              <th>Families</th>
              <th>Description</th>
              <th>FSM State</th>
              <th>Prefixes (R / A / Adv)</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="session in filteredSessions"
              :key="session.neighbor_address"
              class="peer-row"
              :class="{
                'row-selected': selectedPeerAddress === session.neighbor_address,
                'row-discovered': !session.is_managed,
              }"
              @click="selectPeer(session.neighbor_address)"
              title="Click to view detailed session telemetry and routing parameters"
            >
              <!-- Neighbor Address & IP version -->
              <td>
                <div class="neighbor-cell font-mono">
                  <span class="text-white font-semibold">{{ session.neighbor_address }}</span>
                  <span class="ip-version-pill">{{ session.ip_version === 6 ? 'v6' : 'v4' }}</span>
                </div>
              </td>

              <!-- Origin & Sync Status -->
              <td>
                <div class="origin-sync-cell">
                  <!-- Origin Badge -->
                  <span
                    :class="['origin-badge', session.is_managed ? 'origin-managed' : 'origin-discovered']"
                  >
                    <CheckCircle2 v-if="session.is_managed" :size="11" />
                    <Radio v-else :size="11" />
                    {{ session.is_managed ? 'Managed' : 'Discovered' }}
                  </span>

                  <!-- Sync Status Pill -->
                  <span :class="['sync-pill', `sync-${session.sync_status}`]">
                    <span class="sync-dot"></span>
                    <span class="sync-label">{{ session.sync_status.replace('_', ' ') }}</span>
                  </span>
                </div>
              </td>

              <!-- Session Type & Remote ASN -->
              <td>
                <div class="asn-cell font-mono">
                  <span
                    :class="['session-badge', session.session_type === 'iBGP' ? 'session-ibgp' : 'session-ebgp']"
                  >
                    {{ session.session_type }}
                  </span>
                  <span class="font-medium text-white">AS{{ session.peer_as }}</span>
                </div>
              </td>

              <!-- Capabilities & Flags -->
              <td>
                <div class="badges-row">
                  <span
                    v-if="session.config?.multihop_enabled"
                    class="feature-badge badge-multihop"
                    :title="`eBGP Multi-Hop (TTL: ${session.config.multihop_ttl})`"
                  >
                    Multi-Hop (TTL: {{ session.config.multihop_ttl }})
                  </span>
                  <span
                    v-if="session.config?.md5_password"
                    class="feature-badge badge-md5"
                    title="TCP MD5 Authentication Active"
                  >
                    <ShieldCheck :size="12" /> MD5
                  </span>
                  <span
                    v-if="session.config?.passive_mode"
                    class="feature-badge badge-passive"
                    title="Passive Mode (Listen Only)"
                  >
                    Passive
                  </span>
                  <span
                    v-if="!session.is_managed"
                    class="feature-badge badge-unmanaged"
                    title="Session is active in GoBGP memory but not persisted in Gabu database"
                  >
                    Runtime Only
                  </span>
                  <span
                    v-if="session.is_managed && !session.config?.multihop_enabled && !session.config?.md5_password && !session.config?.passive_mode"
                    class="text-xs text-muted"
                  >
                    Standard
                  </span>
                </div>
              </td>

              <!-- Address Families -->
              <td>
                <div class="family-pills">
                  <template v-if="session.config?.families && session.config.families.length > 0">
                    <span
                      v-for="fam in session.config.families"
                      :key="String(fam)"
                      class="fam-pill"
                    >
                      {{ String(fam).replace('-unicast', '-uni').replace('-flowspec', '-fs') }}
                    </span>
                  </template>
                  <span v-else class="text-xs text-muted font-mono">Dynamic</span>
                </div>
              </td>

              <!-- Description -->
              <td class="text-muted text-sm description-cell">
                {{ session.description || '—' }}
              </td>

              <!-- FSM State -->
              <td>
                <StatusBadge :status="session.state" />
              </td>

              <!-- Prefixes Recv / Accepted / Advertised -->
              <td>
                <div class="prefix-counters font-mono text-sm">
                  <span title="Prefixes Received">{{ session.prefixes_received ?? 0 }}</span>
                  <span class="sep">/</span>
                  <span class="text-green" title="Prefixes Accepted">{{ session.prefixes_accepted ?? 0 }}</span>
                  <span class="sep">/</span>
                  <span class="text-blue" title="Prefixes Advertised">{{ session.prefixes_advertised ?? 0 }}</span>
                </div>
              </td>

              <!-- Actions (Admin or Read-only) -->
              <td class="text-right" @click.stop>
                <div v-if="authStore.isAdmin" class="action-btn-group">
                  <!-- For Managed peers: Soft Reset, Edit, Delete -->
                  <template v-if="session.is_managed">
                    <button
                      class="btn-icon"
                      @click.stop="handleResetPeer(session, true)"
                      title="Soft Reset (RFC 2918 Route Refresh)"
                    >
                      <RotateCcw :size="15" />
                    </button>
                    <button
                      class="btn-icon"
                      @click.stop="openEditPeerModal(session)"
                      title="Edit Peer Settings"
                    >
                      <Pencil :size="15" />
                    </button>
                    <button
                      class="btn-icon text-danger"
                      @click.stop="handleDeletePeer(session)"
                      title="Delete Peer Configuration"
                    >
                      <Trash2 :size="15" />
                    </button>
                  </template>

                  <!-- For Discovered peers: Adopt to DB -->
                  <template v-else>
                    <button
                      class="btn btn-adopt btn-sm"
                      @click.stop="openAdoptPeerModal(session)"
                      title="Adopt discovered BGP session into persistent Gabu database configuration"
                    >
                      <ArrowDownToLine :size="14" />
                      <span>Adopt to DB</span>
                    </button>
                  </template>
                </div>
                <div v-else class="text-muted text-xs">
                  Read-Only
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Peer Session Inspector Drawer / Card -->
    <div v-if="selectedSession" class="card inspector-card mt-4">
      <div class="card-header-row">
        <div class="flex items-center gap-3">
          <div class="inspector-badge">
            <Radio :size="20" class="text-primary" />
          </div>
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <h3 class="card-title font-mono">{{ selectedSession.neighbor_address }}</h3>
              <span class="ip-version-pill">{{ selectedSession.ip_version === 6 ? 'IPv6' : 'IPv4' }}</span>
              <span
                :class="['session-badge', selectedSession.session_type === 'iBGP' ? 'session-ibgp' : 'session-ebgp']"
              >
                {{ selectedSession.session_type }} (AS{{ selectedSession.peer_as }})
              </span>
              <span
                :class="['origin-badge', selectedSession.is_managed ? 'origin-managed' : 'origin-discovered']"
              >
                {{ selectedSession.is_managed ? 'Managed in DB' : 'Discovered (Unmanaged)' }}
              </span>
              <StatusBadge :status="selectedSession.state" />
            </div>
            <p class="card-subtitle mt-1">
              {{ selectedSession.description || 'Observed BGP peering session' }}
            </p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <!-- Inspector Quick Actions -->
          <template v-if="authStore.isAdmin">
            <template v-if="selectedSession.is_managed">
              <button
                class="btn btn-secondary btn-sm"
                @click.stop="handleResetPeer(selectedSession, true)"
                title="Soft Reset session"
              >
                <RotateCcw :size="14" />
                <span>Soft Reset</span>
              </button>
              <button
                class="btn btn-secondary btn-sm"
                @click.stop="openEditPeerModal(selectedSession)"
                title="Edit configuration"
              >
                <Pencil :size="14" />
                <span>Edit</span>
              </button>
            </template>
            <template v-else>
              <button
                class="btn btn-adopt btn-sm"
                @click.stop="openAdoptPeerModal(selectedSession)"
                title="Adopt session into persistent database"
              >
                <ArrowDownToLine :size="14" />
                <span>Adopt to DB</span>
              </button>
            </template>
          </template>
          <button class="btn btn-secondary btn-sm" @click="selectedPeerAddress = null">
            <span>✕ Close</span>
          </button>
        </div>
      </div>

      <!-- Discovered notice banner if session is unmanaged -->
      <div v-if="!selectedSession.is_managed" class="inspector-unmanaged-notice">
        <Radio :size="18" class="text-warning flex-shrink-0" />
        <div class="notice-content">
          <strong>Discovered Runtime Session:</strong> This BGP session is actively maintained by GoBGP, but does not exist in Gabu's database configuration.
          Clicking <strong>Adopt to DB</strong> will persist it, enabling policy attachment and surviving daemon restarts.
        </div>
        <button
          v-if="authStore.isAdmin"
          class="btn btn-adopt btn-sm"
          @click="openAdoptPeerModal(selectedSession)"
        >
          <ArrowDownToLine :size="13" />
          <span>Adopt Now</span>
        </button>
      </div>

      <!-- Inspector Grid: FSM State, Timers, Counters, Capabilities -->
      <div class="inspector-grid">
        <div class="inspector-box">
          <div class="inspect-label">Session Uptime</div>
          <div class="inspect-value font-mono">{{ formatUptime(selectedSession.uptime) }}</div>
        </div>
        <div class="inspector-box">
          <div class="inspect-label">BGP Messages (Rx / Tx)</div>
          <div class="inspect-value font-mono">
            {{ selectedSession.messages_received ?? 0 }} / {{ selectedSession.messages_sent ?? 0 }}
          </div>
        </div>
        <div class="inspector-box">
          <div class="inspect-label">Prefixes (Recv / Acc / Adv)</div>
          <div class="inspect-value font-mono">
            <span>{{ selectedSession.prefixes_received ?? 0 }}</span> /
            <span class="text-green">{{ selectedSession.prefixes_accepted ?? 0 }}</span> /
            <span class="text-blue">{{ selectedSession.prefixes_advertised ?? 0 }}</span>
          </div>
        </div>
        <div class="inspector-box">
          <div class="inspect-label">Transport / Timers</div>
          <div class="inspect-value text-xs font-mono">
            <template v-if="selectedSession.config">
              Hold: {{ selectedSession.config.hold_time }}s | Keepalive: {{ selectedSession.config.keepalive_interval }}s
            </template>
            <template v-else>
              Observed GoBGP Runtime Session
            </template>
          </div>
        </div>
      </div>

      <!-- Capabilities & Families Bar -->
      <div class="inspector-footer">
        <div class="inspect-row">
          <span class="text-xs text-muted uppercase font-semibold">Capabilities:</span>
          <template v-if="selectedSession.config">
            <span v-if="selectedSession.config.multihop_enabled" class="feature-badge badge-multihop">
              eBGP Multi-Hop (TTL: {{ selectedSession.config.multihop_ttl }})
            </span>
            <span v-if="selectedSession.config.md5_password" class="feature-badge badge-md5">
              <ShieldCheck :size="12" /> TCP MD5 Authenticated
            </span>
            <span v-if="selectedSession.config.passive_mode" class="feature-badge badge-passive">
              Passive Mode
            </span>
            <span
              v-if="!selectedSession.config.multihop_enabled && !selectedSession.config.md5_password && !selectedSession.config.passive_mode"
              class="text-xs text-muted"
            >
              Direct Single-Hop, Active Mode, Standard TCP
            </span>
          </template>
          <template v-else>
            <span class="feature-badge badge-unmanaged">Runtime GoBGP Neighbor</span>
          </template>
        </div>

        <div class="inspect-row mt-2">
          <span class="text-xs text-muted uppercase font-semibold">Address Families:</span>
          <template v-if="selectedSession.config?.families && selectedSession.config.families.length > 0">
            <span
              v-for="fam in selectedSession.config.families"
              :key="String(fam)"
              class="fam-pill"
            >
              {{ String(fam) }}
            </span>
          </template>
          <template v-else>
            <span class="text-xs text-muted font-mono">Dynamic / Negotiated on connect</span>
          </template>
        </div>
      </div>
    </div>

    <!-- Global Config Modal -->
    <GlobalConfigModal
      :show="showGlobalModal"
      @close="showGlobalModal = false"
      @saved="refreshAll"
    />

    <!-- Peer Add / Edit / Adopt Modal -->
    <PeerModal
      :show="showPeerModal"
      :peerToEdit="peerToEdit"
      @close="showPeerModal = false"
      @saved="refreshAll"
    />
  </div>
</template>

<style scoped>
.peers-page {
  display: flex;
  flex-direction: column;
}

.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
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

.action-buttons {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

/* Continuous Sync Indicator */
.live-sync-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background-color: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.25);
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  color: #34d399;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  background-color: #10b981;
  border-radius: 50%;
  box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
  animation: pulseGreen 2s infinite cubic-bezier(0.4, 0, 0.6, 1);
}

@keyframes pulseGreen {
  0% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
  }
  70% {
    transform: scale(1);
    box-shadow: 0 0 0 6px rgba(16, 185, 129, 0);
  }
  100% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
  }
}

.sync-text {
  letter-spacing: 0.02em;
}

/* Alert Banner */
.alert-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 18px;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 0.875rem;
}

.alert-banner.success {
  background-color: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #34d399;
}

.alert-banner.error {
  background-color: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #f87171;
}

.alert-banner.info {
  background-color: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: #60a5fa;
}

.banner-close {
  margin-left: auto;
  background: transparent;
  color: currentColor;
  opacity: 0.7;
  font-size: 1rem;
}

.banner-close:hover {
  opacity: 1;
}

/* Router Card */
.router-card {
  padding: 20px 24px;
  background: linear-gradient(180deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.8) 100%);
  border: 1px solid rgba(59, 130, 246, 0.2);
  margin-bottom: 20px;
}

.router-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 20px;
}

.router-identity {
  display: flex;
  align-items: center;
  gap: 16px;
}

.router-avatar {
  background-color: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.3);
  width: 52px;
  height: 52px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.router-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.router-name {
  font-size: 1.25rem;
  font-weight: 700;
  color: #fff;
}

.router-sub {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-top: 3px;
}

.router-metrics {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}

.metric-box {
  display: flex;
  flex-direction: column;
}

.metric-label {
  font-size: 0.725rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-dim);
  margin-bottom: 2px;
}

.metric-value {
  font-size: 0.95rem;
  font-weight: 600;
  color: #fff;
}

.configure-btn {
  margin-left: 8px;
}

/* Card Toolbar */
.card-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 16px;
}

.card-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: #fff;
}

.card-subtitle {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-top: 2px;
}

.toolbar-controls {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

/* Filter Tabs */
.filter-tabs {
  display: flex;
  background-color: #0b1120;
  padding: 3px;
  border-radius: 8px;
  border: 1px solid var(--color-surface-border);
}

.tab-btn {
  background: transparent;
  color: var(--color-text-muted);
  border: none;
  font-size: 0.8rem;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s ease;
}

.tab-btn:hover {
  color: #fff;
}

.tab-btn.tab-active {
  background-color: var(--color-surface-hover);
  color: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

.tab-badge {
  font-size: 0.675rem;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 9999px;
  background-color: rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
}

.tab-badge.badge-blue {
  background-color: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
}

.tab-badge.badge-amber {
  background-color: rgba(245, 158, 11, 0.2);
  color: #fbbf24;
}

.tab-badge.badge-green {
  background-color: rgba(16, 185, 129, 0.2);
  color: #34d399;
}

/* Search Box */
.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 10px;
  color: var(--color-text-dim);
  pointer-events: none;
}

.search-input {
  background-color: #0b1120;
  border: 1px solid var(--color-surface-border);
  color: #fff;
  font-size: 0.8rem;
  padding: 6px 10px 6px 32px;
  border-radius: 6px;
  outline: none;
  width: 200px;
  transition: all 0.15s ease;
}

.search-input:focus {
  border-color: var(--color-primary);
  width: 240px;
}

/* Data Table */
.table-responsive {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.data-table th {
  text-align: left;
  padding: 12px 14px;
  border-bottom: 1px solid var(--color-surface-border);
  color: var(--color-text-muted);
  font-size: 0.725rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.data-table td {
  padding: 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  vertical-align: middle;
}

.peer-row {
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.peer-row:hover {
  background-color: rgba(255, 255, 255, 0.03);
}

.peer-row.row-selected {
  background-color: rgba(59, 130, 246, 0.12);
  border-left: 3px solid var(--color-primary);
}

.peer-row.row-discovered {
  background-color: rgba(245, 158, 11, 0.02);
}

.peer-row.row-discovered:hover {
  background-color: rgba(245, 158, 11, 0.05);
}

.neighbor-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ip-version-pill {
  font-size: 0.675rem;
  background-color: #0b1120;
  border: 1px solid #334155;
  color: #94a3b8;
  padding: 1px 5px;
  border-radius: 4px;
}

/* Origin & Sync Cell */
.origin-sync-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.origin-badge {
  font-size: 0.675rem;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 9999px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  width: fit-content;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.origin-managed {
  background-color: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.origin-discovered {
  background-color: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.sync-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 0.675rem;
  color: var(--color-text-dim);
}

.sync-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #64748b;
}

.sync-in_sync .sync-dot {
  background-color: #10b981;
}

.sync-discovered .sync-dot {
  background-color: #f59e0b;
}

.sync-drift .sync-dot {
  background-color: #ef4444;
}

.sync-connecting .sync-dot {
  background-color: #06b6d4;
}

.sync-label {
  text-transform: capitalize;
}

/* ASN Cell */
.asn-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.session-badge {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 9999px;
  text-transform: uppercase;
}

.session-ibgp {
  background-color: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.session-ebgp {
  background-color: rgba(168, 85, 247, 0.15);
  color: #c084fc;
  border: 1px solid rgba(168, 85, 247, 0.3);
}

/* Badges */
.badges-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.feature-badge {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.badge-multihop {
  background-color: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.badge-md5 {
  background-color: rgba(6, 182, 212, 0.15);
  color: #22d3ee;
  border: 1px solid rgba(6, 182, 212, 0.3);
}

.badge-passive {
  background-color: rgba(148, 163, 184, 0.15);
  color: #cbd5e1;
  border: 1px solid rgba(148, 163, 184, 0.3);
}

.badge-unmanaged {
  background-color: rgba(245, 158, 11, 0.12);
  color: #fbbf24;
  border: 1px dashed rgba(245, 158, 11, 0.4);
}

.family-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.fam-pill {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  background-color: #0b1120;
  border: 1px solid #334155;
  color: #94a3b8;
  padding: 1px 6px;
  border-radius: 4px;
}

.description-cell {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.prefix-counters {
  display: flex;
  align-items: center;
  gap: 6px;
}

.prefix-counters .sep {
  color: var(--color-text-dim);
}

/* Actions */
.action-btn-group {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 6px;
}

.btn-icon {
  background: transparent;
  color: var(--color-text-dim);
  padding: 6px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  border: none;
  cursor: pointer;
}

.btn-icon:hover {
  color: #fff;
  background-color: var(--color-surface-hover);
}

.btn-icon.text-danger:hover {
  color: #ef4444;
  background-color: rgba(239, 68, 68, 0.15);
}

/* Adopt Button */
.btn-adopt {
  background: linear-gradient(180deg, #10b981 0%, #059669 100%);
  color: #fff;
  border: 1px solid #34d399;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-adopt:hover {
  background: linear-gradient(180deg, #059669 0%, #047857 100%);
  box-shadow: 0 2px 6px rgba(16, 185, 129, 0.4);
}

.btn-sm {
  padding: 4px 10px;
  font-size: 0.75rem;
}

/* Inspector Drawer Card */
.inspector-card {
  border: 1px solid rgba(59, 130, 246, 0.3);
  background: linear-gradient(180deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.9) 100%);
  animation: fadeInScale 0.15s ease-out;
}

.inspector-unmanaged-notice {
  margin-top: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  background-color: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.25);
  border-radius: 8px;
  font-size: 0.8rem;
  color: #fbbf24;
}

.inspector-unmanaged-notice .notice-content {
  line-height: 1.4;
}

.inspector-badge {
  width: 40px;
  height: 40px;
  background-color: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.inspector-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--color-surface-border);
}

.inspector-box {
  background-color: #0b1120;
  border: 1px solid rgba(255, 255, 255, 0.05);
  padding: 12px 14px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.inspect-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-dim);
}

.inspect-value {
  font-size: 0.9rem;
  font-weight: 600;
  color: #fff;
}

.inspector-footer {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.inspect-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.loading-state,
.empty-state {
  padding: 48px;
  text-align: center;
  color: var(--color-text-muted);
}

.empty-icon {
  margin: 0 auto 12px;
  opacity: 0.35;
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.text-green {
  color: #34d399;
}

.text-blue {
  color: #60a5fa;
}

.text-warning {
  color: #fbbf24;
}

.text-danger {
  color: #ef4444;
}

.mt-2 {
  margin-top: 8px;
}

.mt-4 {
  margin-top: 16px;
}

.mb-2 {
  margin-bottom: 8px;
}

.text-right {
  text-align: right;
}
</style>
