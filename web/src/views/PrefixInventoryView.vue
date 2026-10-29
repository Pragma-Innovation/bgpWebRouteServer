<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { usePrefixStore, type IpPrefix } from '../stores/prefixStore'
import { useRoutingStore } from '../stores/routingStore'
import { useAuthStore } from '../stores/authStore'
import { Plus, DownloadCloud, Trash2, ShieldBan, Search, Filter, Globe, Tag, CheckCircle2 } from 'lucide-vue-next'

const prefixStore = usePrefixStore()
const routingStore = useRoutingStore()
const authStore = useAuthStore()

const searchQuery = ref('')
const selectedVersion = ref<string>('ALL')

// Pagination state
const currentPage = ref(1)
const pageSize = ref(50)

// Modals
const showAddModal = ref(false)
const showImportModal = ref(false)
const showBlackholeConfirmModal = ref(false)
const selectedPrefixForRtbh = ref<IpPrefix | null>(null)

// Add form state
const newPrefix = ref({
  prefix: '',
  name: '',
  description: '',
  tagsInput: '',
})

// Import ASN form state
const importAsn = ref<number | ''>('')
const importTag = ref('')
const importV4 = ref(true)
const importV6 = ref(true)
const importResult = ref<any>(null)
const importError = ref<string | null>(null)

async function loadPrefixes() {
  await prefixStore.fetchPrefixes({
    ip_version: selectedVersion.value === 'ALL' ? undefined : selectedVersion.value,
    search: searchQuery.value.trim() || undefined,
    page: currentPage.value,
    page_size: pageSize.value,
  })
}

onMounted(async () => {
  await loadPrefixes()
  await routingStore.fetchPseudoRibs()
})

const totalPages = computed(() => Math.ceil(prefixStore.totalCount / pageSize.value) || 1)

function onVersionChange() {
  currentPage.value = 1
  loadPrefixes()
}

let searchTimer: any = null
function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    loadPrefixes()
  }, 300)
}

function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  loadPrefixes()
}

function onPageSizeChange() {
  currentPage.value = 1
  loadPrefixes()
}

async function handleCreatePrefix() {
  if (!newPrefix.value.prefix) return
  const tags = newPrefix.value.tagsInput
    ? newPrefix.value.tagsInput.split(',').map(s => s.trim()).filter(Boolean)
    : []

  try {
    await prefixStore.createPrefix({
      prefix: newPrefix.value.prefix.trim(),
      name: newPrefix.value.name.trim(),
      description: newPrefix.value.description.trim(),
      tags,
    })
    showAddModal.value = false
    newPrefix.value = { prefix: '', name: '', description: '', tagsInput: '' }
    await loadPrefixes()
  } catch (err: any) {
    alert(err.message || 'Failed to create prefix')
  }
}

async function handleImportAsn() {
  if (!importAsn.value) return
  if (!importV4.value && !importV6.value) return
  importError.value = null
  importResult.value = null
  try {
    const res = await prefixStore.importFromAsn(Number(importAsn.value), importTag.value, {
      import_v4: importV4.value,
      import_v6: importV6.value,
    })
    importResult.value = res
    await loadPrefixes()
  } catch (err: any) {
    importError.value = err.message || 'Import failed'
  }
}

function promptBlackhole(p: IpPrefix) {
  selectedPrefixForRtbh.value = p
  showBlackholeConfirmModal.value = true
}

async function executeBlackhole() {
  if (!selectedPrefixForRtbh.value) return
  try {
    await routingStore.triggerQuickBlackhole(
      selectedPrefixForRtbh.value.id,
      selectedPrefixForRtbh.value.ip_version
    )
    showBlackholeConfirmModal.value = false
    selectedPrefixForRtbh.value = null
    alert('RTBH Blackhole route successfully announced to BGP Loc-RIB!')
  } catch (err: any) {
    alert(err.message || 'Failed to trigger RTBH Blackhole')
  }
}

async function handleDeletePrefix(id: number) {
  if (confirm('Are you sure you want to remove this prefix from the inventory?')) {
    try {
      await prefixStore.deletePrefix(id)
      await loadPrefixes()
    } catch (err: any) {
      alert(err.message || 'Cannot delete prefix (it may have active announcements)')
    }
  }
}
</script>

<template>
  <div class="prefix-page">
    <div class="header-section">
      <div>
        <h1 class="page-title">IP Prefix Inventory</h1>
        <p class="page-subtitle">Unified inventory for IPv4 and IPv6 assets, RIPEstat automated discovery, and RTBH targeting.</p>
      </div>
      <div class="header-actions">
        <button
          class="btn btn-secondary"
          :disabled="!authStore.canEdit"
          @click="showImportModal = true; importResult = null; importError = null;"
        >
          <DownloadCloud :size="18" /> Import from ASN
        </button>
        <button
          class="btn btn-primary"
          :disabled="!authStore.canEdit"
          @click="showAddModal = true"
        >
          <Plus :size="18" /> Add IP Prefix
        </button>
      </div>
    </div>

    <!-- Filters Bar -->
    <div class="filters-bar card">
      <div class="search-box">
        <Search :size="16" class="search-icon" />
        <input
          v-model="searchQuery"
          type="text"
          class="search-input"
          placeholder="Search by prefix or name..."
          @input="onSearchInput"
        />
      </div>

      <div class="filter-group">
        <Filter :size="16" class="filter-icon" />
        <span class="filter-label">Family:</span>
        <select v-model="selectedVersion" class="select-input" @change="onVersionChange">
          <option value="ALL">All Versions</option>
          <option value="4">IPv4 Only</option>
          <option value="6">IPv6 Only</option>
        </select>
      </div>

      <div class="results-count">
        Showing {{ prefixStore.prefixes.length }} of {{ prefixStore.totalCount }} prefixes
      </div>
    </div>

    <!-- Table -->
    <div class="card table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>Prefix (CIDR)</th>
            <th>Family</th>
            <th>Asset Label</th>
            <th>Source / Origin ASN</th>
            <th>Tags</th>
            <th class="text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="prefixStore.loading">
            <td colspan="6" class="text-center py-8 text-muted">
              Loading IP prefixes...
            </td>
          </tr>
          <tr v-else-if="prefixStore.prefixes.length === 0">
            <td colspan="6" class="text-center empty-state">
              No IP prefixes found. Add a prefix manually or discover via ASN query.
            </td>
          </tr>
          <tr v-else v-for="p in prefixStore.prefixes" :key="p.id">
            <td class="font-mono text-bold text-accent">
              {{ p.prefix }}
            </td>
            <td>
              <span class="badge" :class="p.ip_version === 4 ? 'badge-blue' : 'badge-purple'">
                IPv{{ p.ip_version }}
              </span>
            </td>
            <td>
              <div class="font-semibold text-white">{{ p.name || '—' }}</div>
              <div v-if="p.description" class="text-xs text-muted">{{ p.description }}</div>
            </td>
            <td>
              <div class="flex items-center gap-1">
                <span class="badge badge-gray text-xs">{{ p.source }}</span>
                <span v-if="p.origin_asn" class="badge badge-outline text-xs">AS{{ p.origin_asn }}</span>
              </div>
            </td>
            <td>
              <div class="tags-container">
                <span v-for="tag in p.tags" :key="tag" class="tag-pill">
                  {{ tag }}
                </span>
                <span v-if="!p.tags || p.tags.length === 0" class="text-xs text-muted">—</span>
              </div>
            </td>
            <td class="text-right actions-cell">
              <button
                class="btn-icon btn-blackhole"
                :disabled="!authStore.canEdit"
                title="1-Click RTBH Blackhole"
                @click="promptBlackhole(p)"
              >
                <ShieldBan :size="16" />
                <span class="action-btn-text">Blackhole</span>
              </button>
              <button
                class="btn-icon btn-danger"
                :disabled="!authStore.canEdit"
                title="Delete Prefix"
                @click="handleDeletePrefix(p.id)"
              >
                <Trash2 :size="16" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination Bar -->
    <div class="card pagination-bar">
      <div class="text-sm text-muted">
        Showing {{ prefixStore.totalCount > 0 ? (currentPage - 1) * pageSize + 1 : 0 }} to
        {{ Math.min(currentPage * pageSize, prefixStore.totalCount) }} of
        {{ prefixStore.totalCount }} prefixes
      </div>
      <div class="pagination-actions">
        <div class="flex items-center gap-2">
          <span class="text-xs text-muted">Page Size:</span>
          <select v-model="pageSize" class="select-input select-sm" @change="onPageSizeChange">
            <option :value="25">25</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
            <option :value="200">200</option>
          </select>
        </div>
        <div class="flex items-center gap-2">
          <button
            class="btn btn-secondary btn-sm"
            :disabled="currentPage <= 1 || prefixStore.loading"
            @click="goToPage(currentPage - 1)"
          >
            Previous
          </button>
          <span class="text-xs text-muted font-mono px-2">Page {{ currentPage }} / {{ totalPages }}</span>
          <button
            class="btn btn-secondary btn-sm"
            :disabled="currentPage >= totalPages || prefixStore.loading"
            @click="goToPage(currentPage + 1)"
          >
            Next
          </button>
        </div>
      </div>
    </div>

    <!-- Add Prefix Modal -->
    <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
      <div class="modal-content card">
        <h2 class="modal-title">Add IP Prefix to Inventory</h2>
        <div class="form-group">
          <label>Network CIDR *</label>
          <input
            v-model="newPrefix.prefix"
            type="text"
            class="input-field"
            placeholder="e.g. 198.51.100.0/24 or 2001:db8::/32"
          />
          <span class="text-xs text-muted">PostgreSQL native CIDR format. Subnet bits will be normalized.</span>
        </div>
        <div class="form-group">
          <label>Asset Label / Name</label>
          <input
            v-model="newPrefix.name"
            type="text"
            class="input-field"
            placeholder="e.g. Production Web VIPs"
          />
        </div>
        <div class="form-group">
          <label>Description / Notes</label>
          <textarea
            v-model="newPrefix.description"
            class="input-field textarea"
            placeholder="Operational notes or owner details"
          ></textarea>
        </div>
        <div class="form-group">
          <label>Tags (comma-separated)</label>
          <input
            v-model="newPrefix.tagsInput"
            type="text"
            class="input-field"
            placeholder="production, dmz, critical"
          />
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showAddModal = false">Cancel</button>
          <button class="btn btn-primary" @click="handleCreatePrefix">Save Prefix</button>
        </div>
      </div>
    </div>

    <!-- Import from ASN Modal -->
    <div v-if="showImportModal" class="modal-overlay" @click.self="showImportModal = false">
      <div class="modal-content card">
        <h2 class="modal-title">
          <Globe :size="20" class="text-primary inline-block mr-2" />
          Automated ASN Prefix Discovery
        </h2>
        <p class="text-sm text-muted mb-4">
          Queries RIPEstat / RPKI global routing tables to automatically discover and import all announced prefixes for an Autonomous System.
        </p>

        <div class="form-group">
          <label>Autonomous System Number (ASN) *</label>
          <input
            v-model="importAsn"
            type="number"
            class="input-field font-mono"
            placeholder="e.g. 13335, 2914, 15169"
          />
        </div>

        <div class="form-group">
          <label>IP Families to Discover *</label>
          <div class="family-checkboxes flex gap-4 mt-1">
            <label class="checkbox-label flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="importV4" />
              <span>IPv4 Prefixes</span>
            </label>
            <label class="checkbox-label flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="importV6" />
              <span>IPv6 Prefixes</span>
            </label>
          </div>
          <span v-if="!importV4 && !importV6" class="text-xs text-danger">Please select at least one IP family to import.</span>
        </div>

        <div class="form-group">
          <label>Assign Tag (Optional)</label>
          <input
            v-model="importTag"
            type="text"
            class="input-field"
            placeholder="e.g. cloudflare-infra"
          />
        </div>

        <div v-if="importError" class="alert alert-error">
          {{ importError }}
        </div>

        <div v-if="importResult" class="alert alert-success">
          <CheckCircle2 :size="20" class="alert-icon" />
          <div>
            <div class="font-bold">Discovery Complete for AS{{ importResult.asn }}!</div>
            <div class="text-sm mt-1">
              Discovered: <strong>{{ importResult.total_found ?? importResult.discovered_count }}</strong> prefixes
              <span class="text-xs text-muted" v-if="importResult.ipv4_found !== undefined">
                (IPv4: {{ importResult.ipv4_found }}, IPv6: {{ importResult.ipv6_found }})
              </span>
            </div>
            <div class="text-sm">
              Newly Imported: <strong class="text-success">{{ importResult.created ?? importResult.imported_count }}</strong> subnets
              <span class="text-xs text-muted" v-if="importResult.ipv4_created !== undefined">
                (IPv4: {{ importResult.ipv4_created }}, IPv6: {{ importResult.ipv6_created }})
              </span>
            </div>
            <div class="text-xs text-muted mt-1">
              Skipped: {{ importResult.skipped_or_existing ?? importResult.duplicates_skipped }} (duplicates or already in inventory)
            </div>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showImportModal = false">Close</button>
          <button
            class="btn btn-primary"
            :disabled="!importAsn || (!importV4 && !importV6) || prefixStore.importingAsn"
            @click="handleImportAsn"
          >
            {{ prefixStore.importingAsn ? 'Querying RIPEstat...' : 'Start Discovery' }}
          </button>
        </div>
      </div>
    </div>

    <!-- RTBH Quick Confirm Modal -->
    <div v-if="showBlackholeConfirmModal" class="modal-overlay" @click.self="showBlackholeConfirmModal = false">
      <div class="modal-content card border-danger">
        <h2 class="modal-title text-danger">
          <ShieldBan :size="20" class="inline-block mr-2" />
          Trigger Remotely Triggered Blackhole (RTBH)
        </h2>
        <p class="text-sm text-muted mb-4">
          You are about to inject an active BGP announcement for prefix:
        </p>
        <div class="p-3 bg-darker rounded font-mono text-lg text-white mb-4">
          {{ selectedPrefixForRtbh?.prefix }}
        </div>
        <p class="text-sm text-muted mb-4">
          This will advertise the prefix to upstream transit providers and peering partners with RFC 7999 community
          <code class="text-primary">65535:666</code> and discard Next-Hop, dropping all traffic directed toward this asset across the backbone.
        </p>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showBlackholeConfirmModal = false">Cancel</button>
          <button class="btn btn-danger" @click="executeBlackhole">Confirm & Trigger Blackhole</button>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.prefix-page {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
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

.filters-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1.25rem;
  flex-wrap: wrap;
}

.search-box {
  position: relative;
  flex: 1;
  min-width: 250px;
}

.search-icon {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: #64748b;
}

.search-input {
  width: 100%;
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 0.5rem 0.75rem 0.5rem 2.25rem;
  color: #f8fafc;
  font-size: 0.875rem;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.filter-icon {
  color: #64748b;
}

.filter-label {
  font-size: 0.875rem;
  color: #94a3b8;
}

.select-input {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  color: #f8fafc;
  font-size: 0.875rem;
}

.results-count {
  font-size: 0.875rem;
  color: #64748b;
  margin-left: auto;
}

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
  padding: 0.875rem 1rem;
  border-bottom: 1px solid #1e293b;
}

.empty-state {
  padding: 2.5rem;
  color: #64748b;
}

.badge {
  display: inline-block;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.badge-blue {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.badge-purple {
  background: rgba(168, 85, 247, 0.15);
  color: #c084fc;
  border: 1px solid rgba(168, 85, 247, 0.3);
}

.badge-gray {
  background: #1e293b;
  color: #94a3b8;
}

.badge-outline {
  border: 1px solid #475569;
  color: #cbd5e1;
}

.tags-container {
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
  border: 1px solid rgba(56, 189, 248, 0.2);
}

.actions-cell {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.btn-blackhole {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.65rem;
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-blackhole:hover:not(:disabled) {
  background: #ef4444;
  color: white;
}

.btn-icon {
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 0.35rem;
  border-radius: 4px;
  transition: color 0.2s;
}

.btn-danger:hover:not(:disabled) {
  color: #ef4444;
}

/* Modals */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-content {
  width: 100%;
  max-width: 520px;
  padding: 1.75rem;
  border-radius: 8px;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #fff;
  margin-bottom: 1rem;
}

.form-group {
  margin-bottom: 1.25rem;
}

.form-group label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: #cbd5e1;
  margin-bottom: 0.35rem;
}

.input-field {
  width: 100%;
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 0.6rem 0.75rem;
  color: #fff;
  font-size: 0.875rem;
}

.textarea {
  min-height: 70px;
  resize: vertical;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

.border-danger {
  border: 1px solid rgba(239, 68, 68, 0.4);
}

.bg-darker {
  background: #090d16;
}

.alert {
  padding: 0.75rem;
  border-radius: 6px;
  font-size: 0.875rem;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.alert-error {
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #fca5a5;
}

.alert-success {
  background: rgba(34, 197, 94, 0.15);
  border: 1px solid rgba(34, 197, 94, 0.3);
  color: #86efac;
}

/* Pagination Bar */
.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 1rem;
  padding: 0.85rem 1.25rem;
}

.pagination-actions {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.select-sm {
  padding: 0.3rem 0.5rem;
  font-size: 0.8rem;
}

.btn-sm {
  padding: 0.35rem 0.75rem;
  font-size: 0.8rem;
}

.family-checkboxes {
  padding: 0.25rem 0;
}

.checkbox-label {
  color: #cbd5e1;
  font-size: 0.875rem;
}

.cursor-pointer {
  cursor: pointer;
}
</style>
