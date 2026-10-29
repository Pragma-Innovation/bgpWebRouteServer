<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoutingStore, type PseudoRib, type Rib } from '../stores/routingStore'
import { usePrefixStore } from '../stores/prefixStore'
import { useFlowspecStore } from '../stores/flowspecStore'
import { useAuthStore } from '../stores/authStore'
import { Plus, Trash2, Tag, Layers, Send, CheckCircle2, AlertCircle, RefreshCw, X, Search, Filter, ShieldAlert, Database } from 'lucide-vue-next'

const routingStore = useRoutingStore()
const prefixStore = usePrefixStore()
const flowspecStore = useFlowspecStore()
const authStore = useAuthStore()

const searchQuery = ref('')
const selectedFamily = ref<string>('ALL')

// Modals
const showCreateRibModal = ref(false)
const showMasterRibModal = ref(false)
const showAddMemberModal = ref(false)
const targetPseudoRib = ref<PseudoRib | null>(null)
const selectedPrefixIdToAdd = ref<number | ''>('')
const selectedFlowspecIdToAdd = ref<number | ''>('')

// Create Pseudo-RIB state
const newRib = ref({
  name: '',
  description: '',
  afi_safi: 'ipv4-unicast',
  next_hop: '192.0.2.1',
  local_pref: 100,
  med: null as number | null,
  as_path_prepend: '',
  origin: 'igp',
  is_default: false,
})
const communitiesInput = ref<Array<{ type: 'STANDARD' | 'LARGE'; value: string; description: string }>>([
  { type: 'STANDARD', value: '65535:666', description: 'RFC 7999 BLACKHOLE' }
])

// Create Master RIB state
const newMasterRib = ref({
  name: '',
  description: '',
  selectedPseudoRibIds: [] as number[],
})

onMounted(async () => {
  await routingStore.fetchRibs()
  await routingStore.fetchPseudoRibs()
  await prefixStore.fetchPrefixes()
  await flowspecStore.fetchRules()
})

const filteredRibs = computed(() => {
  return routingStore.pseudoRibs.filter(r => {
    const matchFamily = selectedFamily.value === 'ALL' || r.afi_safi === selectedFamily.value
    const query = searchQuery.value.toLowerCase().trim()
    const matchSearch = !query ||
      r.name.toLowerCase().includes(query) ||
      (r.description && r.description.toLowerCase().includes(query))
    return matchFamily && matchSearch
  })
})

const availablePrefixesForTarget = computed(() => {
  if (!targetPseudoRib.value) return []
  const existingIds = new Set(targetPseudoRib.value.prefixes || [])
  return prefixStore.prefixes.filter(p => p.ip_version === targetPseudoRib.value?.ip_version && !existingIds.has(p.id))
})

const availableFlowspecForTarget = computed(() => {
  if (!targetPseudoRib.value) return []
  const existingIds = new Set(targetPseudoRib.value.flowspec_rules || [])
  const isV4 = targetPseudoRib.value.afi_safi.includes('ipv4')
  return flowspecStore.rules.filter(r => {
    const famMatch = isV4 ? r.addr_fam === 'IPv4' : r.addr_fam === 'IPv6'
    return famMatch && !existingIds.has(r.id)
  })
})

function addCommunityRow() {
  communitiesInput.value.push({ type: 'STANDARD', value: '', description: '' })
}

function removeCommunityRow(idx: number) {
  communitiesInput.value.splice(idx, 1)
}

function applyPreset(preset: 'RTBH' | 'NO_EXPORT' | 'LARGE_SAMPLE') {
  if (preset === 'RTBH') {
    communitiesInput.value.push({ type: 'STANDARD', value: '65535:666', description: 'RFC 7999 BLACKHOLE' })
  } else if (preset === 'NO_EXPORT') {
    communitiesInput.value.push({ type: 'STANDARD', value: '65535:65281', description: 'RFC 1997 NO_EXPORT' })
  } else if (preset === 'LARGE_SAMPLE') {
    communitiesInput.value.push({ type: 'LARGE', value: '65000:666:1', description: 'RFC 8092 Large RTBH' })
  }
}

async function handleCreatePseudoRib() {
  if (!newRib.value.name) return
  try {
    await routingStore.createPseudoRib({
      ...newRib.value,
      communities_input: communitiesInput.value.filter(c => c.value.trim() !== '')
    })
    showCreateRibModal.value = false
    newRib.value = {
      name: '',
      description: '',
      afi_safi: 'ipv4-unicast',
      next_hop: '192.0.2.1',
      local_pref: 100,
      med: null,
      as_path_prepend: '',
      origin: 'igp',
      is_default: false,
    }
  } catch (err: any) {
    alert(err.message || 'Failed to create Pseudo-RIB')
  }
}

async function handleDeletePseudoRib(id: number) {
  if (confirm('Delete this Pseudo-RIB container?')) {
    try {
      await routingStore.deletePseudoRib(id)
    } catch (err: any) {
      alert(err.message || 'Failed to delete Pseudo-RIB')
    }
  }
}

function openAddMember(rib: PseudoRib) {
  targetPseudoRib.value = rib
  selectedPrefixIdToAdd.value = ''
  selectedFlowspecIdToAdd.value = ''
  showAddMemberModal.value = true
}

async function handleAddMember() {
  if (!targetPseudoRib.value) return
  try {
    if (targetPseudoRib.value.afi_safi.includes('flowspec')) {
      if (!selectedFlowspecIdToAdd.value) return
      await routingStore.addFlowspecToPseudoRib(targetPseudoRib.value.id, Number(selectedFlowspecIdToAdd.value))
    } else {
      if (!selectedPrefixIdToAdd.value) return
      await routingStore.addPrefixToPseudoRib(targetPseudoRib.value.id, Number(selectedPrefixIdToAdd.value))
    }
    await routingStore.fetchPseudoRibs()
    showAddMemberModal.value = false
  } catch (err: any) {
    alert(err.message || 'Failed to add route asset')
  }
}

async function handleRemovePrefix(pseudoRibId: number, prefixId: number) {
  try {
    await routingStore.removePrefixFromPseudoRib(pseudoRibId, prefixId)
    await routingStore.fetchPseudoRibs()
  } catch (err: any) {
    alert(err.message || 'Failed to remove prefix')
  }
}

async function handleRemoveFlowspec(pseudoRibId: number, ruleId: number) {
  try {
    await routingStore.removeFlowspecFromPseudoRib(pseudoRibId, ruleId)
    await routingStore.fetchPseudoRibs()
  } catch (err: any) {
    alert(err.message || 'Failed to remove Flowspec rule')
  }
}

async function handlePushMasterRib(ribId: number) {
  try {
    const res = await routingStore.pushRibToBgp(ribId)
    alert(`Successfully pushed ${res.pushed_count} routes to GoBGP Loc-RIB!`)
  } catch (err: any) {
    alert(err.message || 'Push to GoBGP failed')
  }
}

async function handleCreateMasterRib() {
  if (!newMasterRib.value.name) return
  try {
    await routingStore.createRib({
      name: newMasterRib.value.name.trim(),
      description: newMasterRib.value.description.trim(),
      pseudo_ribs: newMasterRib.value.selectedPseudoRibIds,
    })
    showMasterRibModal.value = false
    newMasterRib.value = { name: '', description: '', selectedPseudoRibIds: [] }
  } catch (err: any) {
    alert(err.message || 'Failed to create Master RIB')
  }
}
</script>

<template>
  <div class="pseudo-rib-page">
    <!-- Header -->
    <div class="header-section">
      <div>
        <h1 class="page-title">Pseudo-RIBs & Master Loc-RIB</h1>
        <p class="page-subtitle">Group IPv4/IPv6 prefixes or Flowspec rules into policy containers, assemble into a Master RIB, and push to GoBGP.</p>
      </div>
      <div class="header-actions">
        <button
          v-if="routingStore.activeRib"
          class="btn btn-push"
          :disabled="!authStore.canEdit || routingStore.pushingRib"
          @click="handlePushMasterRib(routingStore.activeRib.id)"
        >
          <RefreshCw :size="18" :class="{ 'spin': routingStore.pushingRib }" />
          {{ routingStore.pushingRib ? 'Pushing to GoBGP...' : `Push '${routingStore.activeRib.name}' to GoBGP` }}
        </button>
        <button
          class="btn btn-secondary"
          :disabled="!authStore.canEdit"
          @click="showMasterRibModal = true"
        >
          <Layers :size="18" /> Manage Master RIBs
        </button>
        <button
          class="btn btn-primary"
          :disabled="!authStore.canEdit"
          @click="showCreateRibModal = true"
        >
          <Plus :size="18" /> New Pseudo-RIB
        </button>
      </div>
    </div>

    <!-- Active Master RIB Banner -->
    <div v-if="routingStore.activeRib" class="card active-rib-banner">
      <div class="flex items-center gap-3">
        <div class="rib-status-icon">
          <Layers :size="24" class="text-primary" />
        </div>
        <div>
          <div class="flex items-center gap-2">
            <span class="font-bold text-white text-base">{{ routingStore.activeRib.name }}</span>
            <span
              class="badge"
              :class="routingStore.activeRib.status === 'SYNCED' ? 'badge-green' : 'badge-amber'"
            >
              {{ routingStore.activeRib.status }}
            </span>
            <span class="badge badge-outline text-xs">Active in GoBGP</span>
          </div>
          <div class="text-xs text-muted mt-1">
            {{ routingStore.activeRib.description || 'Master Loc-RIB configuration' }} •
            Bundling {{ routingStore.activeRib.pseudo_ribs_count }} Pseudo-RIBs ({{ routingStore.activeRib.total_routes_count }} total routes) •
            Last pushed: {{ routingStore.activeRib.last_pushed_at ? new Date(routingStore.activeRib.last_pushed_at).toLocaleTimeString() : 'Never' }}
          </div>
        </div>
      </div>
      <div>
        <button
          class="btn btn-primary btn-sm"
          :disabled="!authStore.canEdit || routingStore.pushingRib"
          @click="handlePushMasterRib(routingStore.activeRib.id)"
        >
          <Send :size="14" /> Push Changes
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
          placeholder="Search Pseudo-RIB profiles by name or description..."
        />
      </div>

      <div class="filter-group">
        <Filter :size="16" class="filter-icon" />
        <span class="filter-label">AFI/SAFI:</span>
        <select v-model="selectedFamily" class="select-input">
          <option value="ALL">All Families</option>
          <option value="ipv4-unicast">IPv4 Unicast (SAFI 1)</option>
          <option value="ipv6-unicast">IPv6 Unicast (SAFI 1)</option>
          <option value="ipv4-flowspec">IPv4 Flowspec (SAFI 133)</option>
          <option value="ipv6-flowspec">IPv6 Flowspec (SAFI 133)</option>
        </select>
      </div>

      <div class="results-count">
        Showing {{ filteredRibs.length }} of {{ routingStore.pseudoRibs.length }} Pseudo-RIBs
      </div>
    </div>

    <!-- Pseudo-RIB Cards Grid -->
    <div class="cards-grid">
      <div v-for="rib in filteredRibs" :key="rib.id" class="card rib-card">
        <div class="rib-header">
          <div class="flex items-center gap-2">
            <span
              class="badge"
              :class="rib.afi_safi.includes('flowspec') ? 'badge-amber' : (rib.ip_version === 4 ? 'badge-blue' : 'badge-purple')"
            >
              {{ rib.afi_safi }}
            </span>
            <span v-if="rib.is_default" class="badge badge-green">Default</span>
          </div>
          <button
            v-if="authStore.isAdmin"
            class="btn-icon btn-danger"
            title="Delete Profile"
            @click="handleDeletePseudoRib(rib.id)"
          >
            <Trash2 :size="16" />
          </button>
        </div>

        <h3 class="rib-title">{{ rib.name }}</h3>
        <p class="rib-desc">{{ rib.description || 'No description provided.' }}</p>

        <!-- BGP Path Attributes -->
        <div class="rib-specs">
          <div v-if="!rib.afi_safi.includes('flowspec')" class="spec-row">
            <span class="spec-label">Next-Hop:</span>
            <span class="spec-value font-mono">{{ rib.next_hop || 'Self / Peer default' }}</span>
          </div>
          <div class="spec-row">
            <span class="spec-label">Local Preference:</span>
            <span class="spec-value">{{ rib.local_pref }}</span>
          </div>
          <div v-if="rib.med" class="spec-row">
            <span class="spec-label">MED:</span>
            <span class="spec-value">{{ rib.med }}</span>
          </div>
        </div>

        <!-- Community Tags -->
        <div class="rib-communities">
          <div class="text-xs text-muted mb-1 font-semibold flex items-center gap-1">
            <Tag :size="12" /> BGP Communities ({{ rib.communities?.length || 0 }}):
          </div>
          <div class="community-tags">
            <div
              v-for="comm in rib.communities"
              :key="comm.id"
              class="community-pill"
              :class="comm.community_type === 'LARGE' ? 'pill-large' : 'pill-standard'"
            >
              <span class="font-mono">{{ comm.value }}</span>
            </div>
            <div v-if="!rib.communities || rib.communities.length === 0" class="text-xs text-muted">
              None
            </div>
          </div>
        </div>

        <!-- MEMBER ROUTE ASSETS CONTAINER -->
        <div class="member-assets-section">
          <div class="flex justify-between items-center mb-2">
            <span class="text-xs font-bold text-white flex items-center gap-1">
              <span v-if="rib.afi_safi.includes('flowspec')"><ShieldAlert :size="14" class="text-amber" /> Member Flowspec Rules ({{ rib.flowspec_rules_count || 0 }})</span>
              <span v-else><Database :size="14" class="text-blue" /> Member Prefixes ({{ rib.prefixes_count || 0 }})</span>
            </span>
            <button
              class="btn-add-entry"
              :disabled="!authStore.canEdit"
              @click="openAddMember(rib)"
            >
              <Plus :size="12" /> Add
            </button>
          </div>

          <!-- Unicast Member Prefixes -->
          <div v-if="!rib.afi_safi.includes('flowspec')" class="members-list">
            <div
              v-for="p in rib.prefixes_details"
              :key="p.id"
              class="member-pill font-mono"
            >
              <span>{{ p.prefix }}</span>
              <button
                class="btn-remove-member"
                :disabled="!authStore.canEdit"
                @click="handleRemovePrefix(rib.id, p.id)"
                title="Remove prefix"
              >
                <X :size="12" />
              </button>
            </div>
            <div v-if="!rib.prefixes_details || rib.prefixes_details.length === 0" class="text-xs text-muted italic">
              No prefixes in this Pseudo-RIB. Click '+ Add' to attach.
            </div>
          </div>

          <!-- Flowspec Member Rules -->
          <div v-else class="members-list">
            <div
              v-for="r in rib.flowspec_rules_details"
              :key="r.id"
              class="member-pill"
            >
              <span class="font-mono text-xs">{{ r.dst_prefix || 'any' }} port {{ r.dst_port || 'any' }} &rarr; {{ r.action }}</span>
              <button
                class="btn-remove-member"
                :disabled="!authStore.canEdit"
                @click="handleRemoveFlowspec(rib.id, r.id)"
                title="Remove Flowspec rule"
              >
                <X :size="12" />
              </button>
            </div>
            <div v-if="!rib.flowspec_rules_details || rib.flowspec_rules_details.length === 0" class="text-xs text-muted italic">
              No Flowspec rules in this Pseudo-RIB. Click '+ Add' to attach.
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- Add Member Modal -->
    <div v-if="showAddMemberModal" class="modal-overlay" @click.self="showAddMemberModal = false">
      <div class="modal-content card">
        <h2 class="modal-title">
          Add Route Asset to '{{ targetPseudoRib?.name }}'
        </h2>
        <p class="text-sm text-muted mb-4">
          Select an asset to attach to this {{ targetPseudoRib?.afi_safi }} container.
        </p>

        <!-- Unicast Selector -->
        <div v-if="!targetPseudoRib?.afi_safi.includes('flowspec')" class="form-group">
          <label>Select IP Prefix from Inventory *</label>
          <select v-model="selectedPrefixIdToAdd" class="input-field select-input">
            <option value="" disabled>Choose prefix...</option>
            <option v-for="p in availablePrefixesForTarget" :key="p.id" :value="p.id">
              {{ p.prefix }} — {{ p.name || 'Untitled' }} (AS{{ p.origin_asn || 'Local' }})
            </option>
          </select>
          <div v-if="availablePrefixesForTarget.length === 0" class="text-xs text-amber mt-1">
            No compatible IPv{{ targetPseudoRib?.ip_version }} prefixes available. Add some in Prefix Inventory first.
          </div>
        </div>

        <!-- Flowspec Selector -->
        <div v-else class="form-group">
          <label>Select Flowspec Rule *</label>
          <select v-model="selectedFlowspecIdToAdd" class="input-field select-input">
            <option value="" disabled>Choose Flowspec rule...</option>
            <option v-for="r in availableFlowspecForTarget" :key="r.id" :value="r.id">
              #{{ r.id }} {{ r.name }} ({{ r.dst_prefix || 'any' }} &rarr; {{ r.action }})
            </option>
          </select>
          <div v-if="availableFlowspecForTarget.length === 0" class="text-xs text-amber mt-1">
            No compatible Flowspec rules available. Create rules in Flowspec Rules view first.
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showAddMemberModal = false">Cancel</button>
          <button
            class="btn btn-primary"
            :disabled="(!selectedPrefixIdToAdd && !selectedFlowspecIdToAdd)"
            @click="handleAddMember"
          >
            Attach Asset
          </button>
        </div>
      </div>
    </div>

    <!-- Master RIB Manager Modal -->
    <div v-if="showMasterRibModal" class="modal-overlay" @click.self="showMasterRibModal = false">
      <div class="modal-content card modal-lg">
        <h2 class="modal-title">Master RIB Configuration</h2>
        <p class="text-sm text-muted mb-4">
          A Master RIB bundles multiple Pseudo-RIBs and is synchronized to GoBGP.
        </p>

        <!-- Existing RIBs List -->
        <div class="existing-ribs mb-4">
          <div
            v-for="r in routingStore.ribs"
            :key="r.id"
            class="rib-bundle-row"
            :class="{ 'border-active': r.is_active }"
          >
            <div class="flex-1">
              <div class="flex items-center gap-2">
                <span class="font-bold text-white">{{ r.name }}</span>
                <span v-if="r.is_active" class="badge badge-green text-xs">Active Loc-RIB</span>
                <span class="badge badge-gray text-xs">{{ r.status }}</span>
              </div>
              <div class="text-xs text-muted mt-1">
                Bundling {{ r.pseudo_ribs_count }} Pseudo-RIBs • {{ r.total_routes_count }} total routes
              </div>
            </div>
            <div class="flex items-center gap-2">
              <button
                class="btn btn-primary btn-sm"
                :disabled="!authStore.canEdit || routingStore.pushingRib"
                @click="handlePushMasterRib(r.id)"
              >
                <Send :size="14" /> Push to GoBGP
              </button>
            </div>
          </div>
        </div>

        <!-- Create New Master RIB -->
        <div class="border-top pt-4">
          <h3 class="text-sm font-bold text-white mb-2">Create New Master RIB</h3>
          <div class="form-grid mb-2">
            <div class="form-group">
              <label>RIB Name *</label>
              <input v-model="newMasterRib.name" type="text" class="input-field" placeholder="e.g. Lab Peering RIB" />
            </div>
            <div class="form-group">
              <label>Description</label>
              <input v-model="newMasterRib.description" type="text" class="input-field" placeholder="Optional notes" />
            </div>
          </div>
          <div class="form-group">
            <label class="mb-1 block text-sm">Select Pseudo-RIBs to bundle:</label>
            <div class="pseudo-rib-checkboxes">
              <label
                v-for="pr in routingStore.pseudoRibs"
                :key="pr.id"
                class="checkbox-chip"
                :class="{ 'chip-selected': newMasterRib.selectedPseudoRibIds.includes(pr.id) }"
              >
                <input
                  type="checkbox"
                  :value="pr.id"
                  v-model="newMasterRib.selectedPseudoRibIds"
                />
                <span>{{ pr.name }} ({{ pr.afi_safi }})</span>
              </label>
            </div>
          </div>
          <button class="btn btn-primary btn-sm" :disabled="!newMasterRib.name" @click="handleCreateMasterRib">
            Save Master RIB
          </button>
        </div>

        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showMasterRibModal = false">Close</button>
        </div>
      </div>
    </div>

    <!-- Create Pseudo-RIB Modal -->
    <div v-if="showCreateRibModal" class="modal-overlay" @click.self="showCreateRibModal = false">
      <div class="modal-content card modal-lg">
        <h2 class="modal-title">Create Pseudo-RIB Container</h2>

        <div class="form-grid">
          <div class="form-group">
            <label>Profile Name *</label>
            <input v-model="newRib.name" type="text" class="input-field" placeholder="e.g. RTBH Upstream Discard" />
          </div>

          <div class="form-group">
            <label>Address Family (AFI/SAFI) *</label>
            <select v-model="newRib.afi_safi" class="input-field select-input">
              <option value="ipv4-unicast">IPv4 Unicast (AFI 1, SAFI 1)</option>
              <option value="ipv6-unicast">IPv6 Unicast (AFI 2, SAFI 1)</option>
              <option value="ipv4-flowspec">IPv4 Flowspec (AFI 1, SAFI 133)</option>
              <option value="ipv6-flowspec">IPv6 Flowspec (AFI 2, SAFI 133)</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label>Description</label>
          <input v-model="newRib.description" type="text" class="input-field" placeholder="Policy purpose of this container" />
        </div>

        <div v-if="!newRib.afi_safi.includes('flowspec')" class="form-grid">
          <div class="form-group">
            <label>Next-Hop Address</label>
            <input v-model="newRib.next_hop" type="text" class="input-field font-mono" placeholder="192.0.2.1 or 100::1" />
          </div>

          <div class="form-group">
            <label>Local Preference</label>
            <input v-model="newRib.local_pref" type="number" class="input-field" placeholder="100" />
          </div>
        </div>

        <!-- Communities Section -->
        <div class="communities-builder">
          <div class="flex justify-between items-center mb-2">
            <label class="font-semibold text-white text-sm">BGP Community Tags</label>
            <div class="presets-row">
              <button type="button" class="btn-preset" @click="applyPreset('RTBH')">+ RFC 7999 Blackhole</button>
              <button type="button" class="btn-preset" @click="applyPreset('NO_EXPORT')">+ NO_EXPORT</button>
              <button type="button" class="btn-preset" @click="applyPreset('LARGE_SAMPLE')">+ Large (RFC 8092)</button>
            </div>
          </div>

          <div v-for="(comm, idx) in communitiesInput" :key="idx" class="comm-input-row">
            <select v-model="comm.type" class="comm-type-select">
              <option value="STANDARD">Standard</option>
              <option value="LARGE">Large</option>
            </select>
            <input v-model="comm.value" type="text" class="input-field font-mono flex-1" placeholder="65535:666" />
            <input v-model="comm.description" type="text" class="input-field flex-1" placeholder="Description" />
            <button type="button" class="btn-icon btn-danger" @click="removeCommunityRow(idx)">
              <Trash2 :size="16" />
            </button>
          </div>

          <button type="button" class="btn-add-comm" @click="addCommunityRow">
            <Plus :size="14" /> Add Tag
          </button>
        </div>

        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showCreateRibModal = false">Cancel</button>
          <button class="btn btn-primary" @click="handleCreatePseudoRib">Create Container</button>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.pseudo-rib-page {
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

.active-rib-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-left: 4px solid #10b981;
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

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(370px, 1fr));
  gap: 1.25rem;
}

.rib-card {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  border: 1px solid #334155;
}

.rib-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rib-title {
  font-size: 1.15rem;
  font-weight: 600;
  color: #fff;
  margin: 0;
}

.rib-desc {
  font-size: 0.85rem;
  color: #94a3b8;
  margin: 0;
  min-height: 2.2rem;
}

.rib-specs {
  background: #0f172a;
  padding: 0.65rem 0.75rem;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.spec-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
}

.spec-label {
  color: #64748b;
}

.spec-value {
  color: #f1f5f9;
}

.rib-communities {
  padding-top: 0.5rem;
}

.community-tags {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.community-pill {
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-size: 0.75rem;
}

.pill-standard {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.pill-large {
  background: rgba(168, 85, 247, 0.15);
  color: #c084fc;
  border: 1px solid rgba(168, 85, 247, 0.3);
}

/* Member Assets Section */
.member-assets-section {
  background: #090d16;
  border: 1px solid #1e293b;
  border-radius: 6px;
  padding: 0.75rem;
  margin-top: auto;
}

.btn-add-entry {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
}

.btn-add-entry:hover {
  background: #3b82f6;
  color: #fff;
}

.members-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  max-height: 120px;
  overflow-y: auto;
}

.member-pill {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.25rem 0.5rem;
  background: #1e293b;
  border-radius: 4px;
  font-size: 0.75rem;
  color: #e2e8f0;
}

.btn-remove-member {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 0.1rem;
}

.btn-remove-member:hover {
  color: #ef4444;
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
.badge-gray { background: #1e293b; color: #94a3b8; }
.badge-outline { border: 1px solid #475569; color: #cbd5e1; }

.btn-icon {
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 0.35rem;
}

.btn-danger:hover { color: #ef4444; }

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
  max-width: 540px;
  padding: 1.75rem;
  border-radius: 8px;
}

.modal-lg { max-width: 640px; }

.modal-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #fff;
  margin-bottom: 1.25rem;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-group { margin-bottom: 1.25rem; }
.form-group label { display: block; font-size: 0.875rem; font-weight: 500; color: #cbd5e1; margin-bottom: 0.35rem; }

.input-field {
  width: 100%;
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 0.6rem 0.75rem;
  color: #fff;
  font-size: 0.875rem;
}

.communities-builder {
  background: #090d16;
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 1.25rem;
}

.presets-row { display: flex; align-items: center; gap: 0.35rem; }
.btn-preset {
  background: #1e293b;
  border: 1px solid #334155;
  color: #38bdf8;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
}

.comm-input-row { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; align-items: center; }
.comm-type-select { background: #0f172a; border: 1px solid #334155; color: #fff; border-radius: 6px; padding: 0.5rem; font-size: 0.8rem; }

.btn-add-comm {
  background: none;
  border: 1px dashed #475569;
  color: #94a3b8;
  padding: 0.4rem 0.75rem;
  border-radius: 4px;
  font-size: 0.8rem;
  cursor: pointer;
}

.existing-ribs {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.rib-bundle-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #0f172a;
  border: 1px solid #334155;
  padding: 0.75rem 1rem;
  border-radius: 6px;
}

.border-active {
  border-color: #10b981;
}

.pseudo-rib-checkboxes {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  max-height: 120px;
  overflow-y: auto;
}

.checkbox-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: #1e293b;
  border: 1px solid #334155;
  padding: 0.35rem 0.6rem;
  border-radius: 6px;
  font-size: 0.8rem;
  color: #e2e8f0;
  cursor: pointer;
}

.chip-selected {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.15);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
