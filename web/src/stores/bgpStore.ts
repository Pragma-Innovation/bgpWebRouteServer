import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '../api/client'

export interface BgpServerStatus {
  backend: string
  ready: boolean
  router_id?: string
  as_number?: number
  uptime_seconds?: number
  peers_count?: number
  flowspec_rules_active?: number
  version?: string
}

export interface BgpNeighbor {
  neighbor_address: string
  peer_as: number
  local_as?: number
  state: string
  uptime?: string | number
  messages_received?: number
  messages_sent?: number
  prefixes_received?: number
  prefixes_accepted?: number
  prefixes_advertised?: number
  description?: string
}

export interface BgpGlobalConfig {
  id?: number
  local_as: number
  router_id: string
  listen_port: number
  updated_at?: string
}

export interface BgpPeerConfig {
  id?: number
  neighbor_address: string
  ip_version?: number
  peer_as: number
  session_type?: 'iBGP' | 'eBGP'
  description?: string
  is_enabled: boolean
  multihop_enabled: boolean
  multihop_ttl: number
  md5_password?: string
  passive_mode: boolean
  hold_time: number
  keepalive_interval: number
  families: string[]
  created_at?: string
  updated_at?: string
}

export interface BgpUnifiedSession {
  neighbor_address: string
  ip_version: number
  peer_as: number
  session_type: 'iBGP' | 'eBGP'
  description?: string
  origin: 'managed' | 'discovered'
  is_managed: boolean
  sync_status: 'in_sync' | 'discovered' | 'drift' | 'connecting' | 'offline' | 'disabled'
  state: string
  config: BgpPeerConfig | null
  live: BgpNeighbor | null
  uptime?: string | number
  prefixes_received?: number
  prefixes_accepted?: number
  prefixes_advertised?: number
  messages_received?: number
  messages_sent?: number
}

export interface ReconcileResult {
  status: string
  pushed_to_gobgp: string[]
  errors: string[]
  total_sessions: number
  managed_count: number
  discovered_count: number
}

export const useBgpStore = defineStore('bgp', () => {
  const status = ref<BgpServerStatus | null>(null)
  const neighbors = ref<BgpNeighbor[]>([])
  const globalConfig = ref<BgpGlobalConfig | null>(null)
  const peerConfigs = ref<BgpPeerConfig[]>([])
  const sessions = ref<BgpUnifiedSession[]>([])
  
  const loadingStatus = ref(false)
  const loadingNeighbors = ref(false)
  const loadingPeers = ref(false)
  const loadingGlobal = ref(false)
  const loadingSessions = ref(false)
  const loading = computed(() => loadingStatus.value || loadingNeighbors.value || loadingPeers.value || loadingGlobal.value || loadingSessions.value)

  const savingGlobal = ref(false)
  const savingPeer = ref(false)
  const syncingPeers = ref(false)
  const reconciling = ref(false)
  const error = ref<string | null>(null)

  async function fetchStatus() {
    loadingStatus.value = true
    error.value = null
    try {
      const res = await apiClient.get<BgpServerStatus>('/bgp/status/')
      status.value = res.data
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch BGP daemon status'
    } finally {
      loadingStatus.value = false
    }
  }

  async function fetchNeighbors() {
    loadingNeighbors.value = true
    error.value = null
    try {
      const res = await apiClient.get<BgpNeighbor[]>('/bgp/neighbors/')
      neighbors.value = Array.isArray(res.data) ? res.data : []
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch BGP neighbors'
    } finally {
      loadingNeighbors.value = false
    }
  }

  async function fetchGlobalConfig() {
    loadingGlobal.value = true
    error.value = null
    try {
      const res = await apiClient.get<BgpGlobalConfig>('/peers/global/')
      globalConfig.value = res.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to fetch global BGP config'
    } finally {
      loadingGlobal.value = false
    }
  }

  async function updateGlobalConfig(data: Partial<BgpGlobalConfig>) {
    savingGlobal.value = true
    error.value = null
    try {
      const res = await apiClient.patch<BgpGlobalConfig>('/peers/global/', data)
      globalConfig.value = res.data
      return res.data
    } catch (err: any) {
      const msg = err.response?.data?.detail || JSON.stringify(err.response?.data) || err.message
      error.value = msg
      throw new Error(msg)
    } finally {
      savingGlobal.value = false
    }
  }

  async function fetchPeerConfigs() {
    loadingPeers.value = true
    error.value = null
    try {
      const res = await apiClient.get<BgpPeerConfig[]>('/peers/peers/')
      peerConfigs.value = Array.isArray(res.data) ? res.data : []
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to fetch peer configurations'
    } finally {
      loadingPeers.value = false
    }
  }

  async function createPeerConfig(data: Partial<BgpPeerConfig>) {
    savingPeer.value = true
    error.value = null
    try {
      const res = await apiClient.post<BgpPeerConfig>('/peers/peers/', data)
      peerConfigs.value.push(res.data)
      await fetchNeighbors()
      await fetchSessions()
      return res.data
    } catch (err: any) {
      const msg = err.response?.data?.detail || JSON.stringify(err.response?.data) || err.message
      error.value = msg
      throw new Error(msg)
    } finally {
      savingPeer.value = false
    }
  }

  async function updatePeerConfig(id: number, data: Partial<BgpPeerConfig>) {
    savingPeer.value = true
    error.value = null
    try {
      const res = await apiClient.patch<BgpPeerConfig>(`/peers/peers/${id}/`, data)
      const idx = peerConfigs.value.findIndex(p => p.id === id)
      if (idx !== -1) {
        peerConfigs.value[idx] = res.data
      }
      await fetchNeighbors()
      await fetchSessions()
      return res.data
    } catch (err: any) {
      const msg = err.response?.data?.detail || JSON.stringify(err.response?.data) || err.message
      error.value = msg
      throw new Error(msg)
    } finally {
      savingPeer.value = false
    }
  }

  async function deletePeerConfig(id: number) {
    savingPeer.value = true
    error.value = null
    try {
      await apiClient.delete(`/peers/peers/${id}/`)
      peerConfigs.value = peerConfigs.value.filter(p => p.id !== id)
      await fetchNeighbors()
      await fetchSessions()
    } catch (err: any) {
      const msg = err.response?.data?.detail || JSON.stringify(err.response?.data) || err.message
      error.value = msg
      throw new Error(msg)
    } finally {
      savingPeer.value = false
    }
  }

  async function resetPeer(id: number, soft: boolean = true) {
    error.value = null
    try {
      const res = await apiClient.post<{ detail: string }>(`/peers/peers/${id}/reset/`, { soft })
      await fetchNeighbors()
      await fetchSessions()
      return res.data
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message
      error.value = msg
      throw new Error(msg)
    }
  }

  async function syncAllPeers() {
    syncingPeers.value = true
    error.value = null
    try {
      const res = await apiClient.post<{ status: string; synced_peers: string[]; errors: string[] }>('/peers/peers/sync/')
      await fetchNeighbors()
      await fetchPeerConfigs()
      await fetchSessions()
      return res.data
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message
      error.value = msg
      throw new Error(msg)
    } finally {
      syncingPeers.value = false
    }
  }

  async function fetchSessions() {
    loadingSessions.value = true
    error.value = null
    try {
      const res = await apiClient.get<BgpUnifiedSession[]>('/peers/peers/sessions/')
      sessions.value = Array.isArray(res.data) ? res.data : []
      return sessions.value
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to fetch unified peering sessions'
      return []
    } finally {
      loadingSessions.value = false
    }
  }

  async function reconcilePeers() {
    reconciling.value = true
    error.value = null
    try {
      const res = await apiClient.post<ReconcileResult>('/peers/peers/reconcile/')
      await fetchSessions()
      await fetchPeerConfigs()
      await fetchNeighbors()
      return res.data
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to reconcile BGP sessions'
      error.value = msg
      throw new Error(msg)
    } finally {
      reconciling.value = false
    }
  }

  async function adoptPeer(data: Partial<BgpPeerConfig>) {
    savingPeer.value = true
    error.value = null
    try {
      const res = await apiClient.post<BgpPeerConfig>('/peers/peers/adopt/', data)
      await fetchSessions()
      await fetchPeerConfigs()
      await fetchNeighbors()
      return res.data
    } catch (err: any) {
      const msg = err.response?.data?.detail || JSON.stringify(err.response?.data) || err.message
      error.value = msg
      throw new Error(msg)
    } finally {
      savingPeer.value = false
    }
  }

  return {
    status,
    neighbors,
    globalConfig,
    peerConfigs,
    sessions,
    loading,
    loadingPeers,
    loadingStatus,
    loadingNeighbors,
    loadingGlobal,
    loadingSessions,
    savingGlobal,
    savingPeer,
    syncingPeers,
    reconciling,
    error,
    fetchStatus,
    fetchNeighbors,
    fetchGlobalConfig,
    updateGlobalConfig,
    fetchPeerConfigs,
    createPeerConfig,
    updatePeerConfig,
    deletePeerConfig,
    resetPeer,
    syncAllPeers,
    fetchSessions,
    reconcilePeers,
    adoptPeer,
  }
})
