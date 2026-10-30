import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '../api/client'

export interface FlowspecRule {
  id: number
  name: string
  description: string
  is_active?: boolean
  addr_fam: 'IPv4' | 'IPv6'
  dst_prefix: string
  src_prefix: string
  proto_number: string
  port: string
  src_port: string
  dst_port: string
  tcp_flags: string
  icmp_type: string
  icmp_code: string
  packet_len: string
  dscp: string
  ip_frag: string
  action: 'Drop' | 'Shape' | 'Redirect' | 'Mark'
  action_value: string
  pseudo_ribs?: Array<{ id: number; name: string; afi_safi: string }>
  created_at: string
  updated_at: string
}

export const useFlowspecStore = defineStore('flowspec', () => {
  const rules = ref<FlowspecRule[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchRules() {
    try {
      loading.value = true
      error.value = null
      const res = await apiClient.get<{ results: FlowspecRule[] } | FlowspecRule[]>('/flowspec/rules/')
      // Handle pagination or unpaginated response
      if (Array.isArray(res.data)) {
        rules.value = res.data
      } else if (res.data.results) {
        rules.value = res.data.results
      }
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch Flowspec rules'
    } finally {
      loading.value = false
    }
  }

  async function deleteRule(id: number) {
    try {
      await apiClient.delete(`/flowspec/rules/${id}/`)
      rules.value = rules.value.filter(r => r.id !== id)
    } catch (err: any) {
      error.value = err.message || `Failed to delete rule #${id}`
    }
  }

  async function createRule(ruleData: Partial<FlowspecRule>): Promise<FlowspecRule> {
    try {
      loading.value = true
      error.value = null
      const res = await apiClient.post<FlowspecRule>('/flowspec/rules/', ruleData)
      rules.value.unshift(res.data)
      return res.data
    } catch (err: any) {
      error.value = err.message || 'Failed to create Flowspec rule'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    rules,
    loading,
    error,
    fetchRules,
    deleteRule,
    createRule,
  }
})
