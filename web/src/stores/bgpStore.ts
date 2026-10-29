import { defineStore } from 'pinia'
import { ref } from 'vue'
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

export const useBgpStore = defineStore('bgp', () => {
  const status = ref<BgpServerStatus | null>(null)
  const neighbors = ref<BgpNeighbor[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchStatus() {
    try {
      loading.value = true
      error.value = null
      const res = await apiClient.get<BgpServerStatus>('/bgp/status/')
      status.value = res.data
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch BGP daemon status'
    } finally {
      loading.value = false
    }
  }

  async function fetchNeighbors() {
    try {
      loading.value = true
      error.value = null
      const res = await apiClient.get<BgpNeighbor[]>('/bgp/neighbors/')
      neighbors.value = res.data
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch BGP neighbors'
    } finally {
      loading.value = false
    }
  }

  return {
    status,
    neighbors,
    loading,
    error,
    fetchStatus,
    fetchNeighbors,
  }
})
