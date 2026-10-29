import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '../api/client'

export interface IpPrefix {
  id: number
  prefix: string
  ip_version: 4 | 6
  name: string
  description: string
  source: 'MANUAL' | 'RIPE_STAT' | 'IRR' | 'IMPORT'
  origin_asn: number | null
  tags: string[]
  created_at: string
  updated_at: string
}

export interface AsnImportResult {
  asn: number
  total_found: number
  ipv4_found: number
  ipv6_found: number
  created: number
  ipv4_created: number
  ipv6_created: number
  skipped_or_existing: number
  discovered_count?: number
  imported_count?: number
  duplicates_skipped?: number
  imported_prefixes?: string[]
}

export const usePrefixStore = defineStore('prefix', () => {
  const prefixes = ref<IpPrefix[]>([])
  const totalCount = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(50)
  const loading = ref(false)
  const importingAsn = ref(false)
  const error = ref<string | null>(null)

  async function fetchPrefixes(params: {
    ip_version?: number | string
    search?: string
    asn?: string
    page?: number
    page_size?: number
  } = {}) {
    try {
      loading.value = true
      error.value = null

      const queryParams: Record<string, any> = {}
      if (params.ip_version !== undefined && params.ip_version !== 'ALL') {
        queryParams.ip_version = params.ip_version
      }
      if (params.search) {
        queryParams.search = params.search
      }
      if (params.asn) {
        queryParams.asn = params.asn
      }
      if (params.page !== undefined) {
        currentPage.value = params.page
      }
      if (params.page_size !== undefined) {
        pageSize.value = params.page_size
      }

      queryParams.page = currentPage.value
      queryParams.page_size = pageSize.value

      const res = await apiClient.get<any>('/prefixes/', { params: queryParams })
      if (Array.isArray(res.data)) {
        prefixes.value = res.data
        totalCount.value = res.data.length
      } else if (res.data.results) {
        prefixes.value = res.data.results
        totalCount.value = res.data.count ?? res.data.results.length
      }
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to fetch IP prefix inventory'
    } finally {
      loading.value = false
    }
  }

  async function createPrefix(data: Partial<IpPrefix>): Promise<IpPrefix> {
    try {
      loading.value = true
      error.value = null
      const res = await apiClient.post<IpPrefix>('/prefixes/', data)
      prefixes.value.unshift(res.data)
      totalCount.value += 1
      return res.data
    } catch (err: any) {
      const msg = err.response?.data?.prefix?.[0] || err.response?.data?.detail || err.message || 'Failed to create prefix'
      error.value = msg
      throw new Error(msg)
    } finally {
      loading.value = false
    }
  }

  async function deletePrefix(id: number) {
    try {
      await apiClient.delete(`/prefixes/${id}/`)
      prefixes.value = prefixes.value.filter(p => p.id !== id)
      totalCount.value = Math.max(0, totalCount.value - 1)
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || `Failed to delete prefix #${id}`
      throw err
    }
  }

  async function importFromAsn(
    asn: number,
    tag?: string,
    options: { import_v4?: boolean; import_v6?: boolean } = {}
  ): Promise<AsnImportResult> {
    try {
      importingAsn.value = true
      error.value = null
      const payload = {
        asn,
        tag: tag || '',
        import_v4: options.import_v4 ?? true,
        import_v6: options.import_v6 ?? true,
      }
      const res = await apiClient.post<AsnImportResult>('/prefixes/import-asn/', payload)
      // Refresh inventory after import
      await fetchPrefixes({ page: 1 })
      return res.data
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || `Failed to discover prefixes for AS${asn}`
      error.value = msg
      throw new Error(msg)
    } finally {
      importingAsn.value = false
    }
  }

  return {
    prefixes,
    totalCount,
    currentPage,
    pageSize,
    loading,
    importingAsn,
    error,
    fetchPrefixes,
    createPrefix,
    deletePrefix,
    importFromAsn,
  }
})
