import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '../api/client'
import type { IpPrefix } from './prefixStore'

export interface BgpCommunity {
  id?: number
  pseudo_rib?: number
  community_type: 'STANDARD' | 'LARGE' | 'EXTENDED'
  value: string
  description?: string
}

export interface PseudoRib {
  id: number
  name: string
  description: string
  afi_safi: string
  ip_version: 4 | 6
  next_hop: string | null
  local_pref: number
  med: number | null
  as_path_prepend: string
  origin: string
  is_default: boolean
  communities: BgpCommunity[]
  prefixes: number[]
  prefixes_details?: IpPrefix[]
  prefixes_count: number
  flowspec_rules: number[]
  flowspec_rules_details?: any[]
  flowspec_rules_count: number
  created_at: string
  updated_at: string
}

export interface Rib {
  id: number
  name: string
  description: string
  pseudo_ribs: number[]
  pseudo_ribs_details?: PseudoRib[]
  pseudo_ribs_count: number
  total_routes_count: number
  is_active: boolean
  status: 'DRAFT' | 'SYNCED' | 'OUT_OF_SYNC' | 'ERROR'
  last_pushed_at: string | null
  created_at: string
  updated_at: string
}

export interface FlowspecTuple {
  id: number
  name: string
  addr_fam: 'IPv4' | 'IPv6'
  dst_prefix: string
  src_prefix: string
  proto_number: string
  port: string
  src_port: string
  dst_port: string
  tcp_flags: string
  action: string
  action_value: string
}

export interface BgpAnnouncement {
  id: number
  rib: number | null
  rib_name?: string
  pseudo_rib: number
  pseudo_rib_name: string
  afi_safi: string
  prefix: number | null
  prefix_cidr?: string
  flowspec_rule: number | null
  flowspec_tuple?: FlowspecTuple | null
  route_repr: string
  next_hop: string | null
  communities: string[]
  large_communities: string[]
  action: string
  is_active: boolean
  programmed_in_rib: boolean
  status: 'DRAFT' | 'ACTIVE' | 'WITHDRAWN' | 'ERROR'
  error_message: string
  last_synced_at: string | null
  created_at: string
  updated_at: string
}

export const useRoutingStore = defineStore('routing', () => {
  const ribs = ref<Rib[]>([])
  const pseudoRibs = ref<PseudoRib[]>([])
  const announcements = ref<BgpAnnouncement[]>([])
  const activeRib = ref<Rib | null>(null)

  const loadingRibs = ref(false)
  const loadingPseudoRibs = ref(false)
  const loadingAnnouncements = ref(false)
  const pushingRib = ref(false)
  const error = ref<string | null>(null)

  async function fetchRibs() {
    try {
      loadingRibs.value = true
      error.value = null
      const res = await apiClient.get<{ results: Rib[] } | Rib[]>('/routing/ribs/')
      if (Array.isArray(res.data)) {
        ribs.value = res.data
      } else if (res.data.results) {
        ribs.value = res.data.results
      }
      activeRib.value = ribs.value.find(r => r.is_active) || ribs.value[0] || null
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to fetch Master RIBs'
    } finally {
      loadingRibs.value = false
    }
  }

  async function createRib(ribData: Partial<Rib>): Promise<Rib> {
    try {
      loadingRibs.value = true
      error.value = null
      const res = await apiClient.post<Rib>('/routing/ribs/', ribData)
      ribs.value.unshift(res.data)
      return res.data
    } catch (err: any) {
      const msg = err.response?.data?.detail || JSON.stringify(err.response?.data) || err.message
      error.value = msg
      throw new Error(msg)
    } finally {
      loadingRibs.value = false
    }
  }

  async function deleteRib(id: number) {
    try {
      await apiClient.delete(`/routing/ribs/${id}/`)
      ribs.value = ribs.value.filter(r => r.id !== id)
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || `Failed to delete RIB #${id}`
      throw err
    }
  }

  async function pushRibToBgp(id: number): Promise<{ pushed_count: number; errors: string[] }> {
    try {
      pushingRib.value = true
      error.value = null
      const res = await apiClient.post<{ rib: Rib; pushed_count: number; errors: string[] }>(`/routing/ribs/${id}/push/`)
      await fetchRibs()
      await fetchAnnouncements()
      return { pushed_count: res.data.pushed_count, errors: res.data.errors }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to push RIB to GoBGP'
      error.value = msg
      throw new Error(msg)
    } finally {
      pushingRib.value = false
    }
  }

  async function fetchPseudoRibs(params: { afi_safi?: string; ip_version?: number; search?: string } = {}) {
    try {
      loadingPseudoRibs.value = true
      error.value = null
      const res = await apiClient.get<{ results: PseudoRib[] } | PseudoRib[]>('/routing/pseudo-ribs/', { params })
      if (Array.isArray(res.data)) {
        pseudoRibs.value = res.data
      } else if (res.data.results) {
        pseudoRibs.value = res.data.results
      }
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to fetch Pseudo-RIBs'
    } finally {
      loadingPseudoRibs.value = false
    }
  }

  async function createPseudoRib(ribData: any): Promise<PseudoRib> {
    try {
      loadingPseudoRibs.value = true
      error.value = null
      const res = await apiClient.post<PseudoRib>('/routing/pseudo-ribs/', ribData)
      pseudoRibs.value.unshift(res.data)
      return res.data
    } catch (err: any) {
      const msg = err.response?.data?.detail || JSON.stringify(err.response?.data) || err.message
      error.value = msg
      throw new Error(msg)
    } finally {
      loadingPseudoRibs.value = false
    }
  }

  async function deletePseudoRib(id: number) {
    try {
      await apiClient.delete(`/routing/pseudo-ribs/${id}/`)
      pseudoRibs.value = pseudoRibs.value.filter(r => r.id !== id)
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || `Failed to delete Pseudo-RIB #${id}`
      error.value = msg
      throw err
    }
  }

  async function addPrefixToPseudoRib(pseudoRibId: number, prefixId: number) {
    try {
      const res = await apiClient.post<PseudoRib>(`/routing/pseudo-ribs/${pseudoRibId}/add-prefix/`, { prefix_id: prefixId })
      const idx = pseudoRibs.value.findIndex(p => p.id === pseudoRibId)
      if (idx !== -1) pseudoRibs.value[idx] = res.data
      return res.data
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to add prefix to Pseudo-RIB'
      throw new Error(msg)
    }
  }

  async function removePrefixFromPseudoRib(pseudoRibId: number, prefixId: number) {
    try {
      const res = await apiClient.post<PseudoRib>(`/routing/pseudo-ribs/${pseudoRibId}/remove-prefix/`, { prefix_id: prefixId })
      const idx = pseudoRibs.value.findIndex(p => p.id === pseudoRibId)
      if (idx !== -1) pseudoRibs.value[idx] = res.data
      return res.data
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to remove prefix from Pseudo-RIB'
      throw new Error(msg)
    }
  }

  async function addFlowspecToPseudoRib(pseudoRibId: number, ruleId: number) {
    try {
      const res = await apiClient.post<PseudoRib>(`/routing/pseudo-ribs/${pseudoRibId}/add-flowspec/`, { rule_id: ruleId })
      const idx = pseudoRibs.value.findIndex(p => p.id === pseudoRibId)
      if (idx !== -1) pseudoRibs.value[idx] = res.data
      return res.data
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to add Flowspec rule to Pseudo-RIB'
      throw new Error(msg)
    }
  }

  async function removeFlowspecFromPseudoRib(pseudoRibId: number, ruleId: number) {
    try {
      const res = await apiClient.post<PseudoRib>(`/routing/pseudo-ribs/${pseudoRibId}/remove-flowspec/`, { rule_id: ruleId })
      const idx = pseudoRibs.value.findIndex(p => p.id === pseudoRibId)
      if (idx !== -1) pseudoRibs.value[idx] = res.data
      return res.data
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to remove Flowspec rule from Pseudo-RIB'
      throw new Error(msg)
    }
  }

  async function fetchAnnouncements(params: any = {}) {
    try {
      loadingAnnouncements.value = true
      error.value = null
      const res = await apiClient.get<{ results: BgpAnnouncement[] } | BgpAnnouncement[]>('/routing/announcements/', { params })
      if (Array.isArray(res.data)) {
        announcements.value = res.data
      } else if (res.data.results) {
        announcements.value = res.data.results
      }
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to fetch BGP announcements'
    } finally {
      loadingAnnouncements.value = false
    }
  }

  async function triggerQuickBlackhole(prefixId: number, ipVersion: 4 | 6) {
    const afi = ipVersion === 6 ? 'ipv6-unicast' : 'ipv4-unicast'
    if (pseudoRibs.value.length === 0) {
      await fetchPseudoRibs()
    }
    const rtbhRib = pseudoRibs.value.find(r => r.afi_safi === afi && (r.is_default || r.name.toLowerCase().includes('blackhole')))
    if (!rtbhRib) {
      throw new Error(`No default RTBH Blackhole Pseudo-RIB profile found for IPv${ipVersion}.`)
    }
    await addPrefixToPseudoRib(rtbhRib.id, prefixId)
    if (ribs.value.length === 0) {
      await fetchRibs()
    }
    if (activeRib.value) {
      await pushRibToBgp(activeRib.value.id)
    }
  }

  return {
    ribs,
    pseudoRibs,
    announcements,
    activeRib,
    loadingRibs,
    loadingPseudoRibs,
    loadingAnnouncements,
    pushingRib,
    error,
    fetchRibs,
    createRib,
    deleteRib,
    pushRibToBgp,
    fetchPseudoRibs,
    createPseudoRib,
    deletePseudoRib,
    addPrefixToPseudoRib,
    removePrefixFromPseudoRib,
    addFlowspecToPseudoRib,
    removeFlowspecFromPseudoRib,
    fetchAnnouncements,
    triggerQuickBlackhole,
  }
})
