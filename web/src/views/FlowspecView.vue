<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useFlowspecStore } from '../stores/flowspecStore'
import { useAuthStore } from '../stores/authStore'
import StatusBadge from '../components/StatusBadge.vue'
import RuleBuilderModal from '../components/RuleBuilderModal.vue'
import { Plus, Trash2, Power, Filter, FileText } from 'lucide-vue-next'

const flowspecStore = useFlowspecStore()
const authStore = useAuthStore()
const selectedFamily = ref<string>('ALL')
const selectedAction = ref<string>('ALL')
const showCreateModal = ref(false)

onMounted(() => {
  flowspecStore.fetchRules()
})

const filteredRules = computed(() => {
  return flowspecStore.rules.filter(rule => {
    const matchFamily = selectedFamily.value === 'ALL' || rule.addr_fam === selectedFamily.value
    const matchAction = selectedAction.value === 'ALL' || rule.action === selectedAction.value
    return matchFamily && matchAction
  })
})
</script>

<template>
  <div class="flowspec-page">
    <div class="header-section">
      <div>
        <h1 class="page-title">BGP Flowspec Mitigation Rules</h1>
        <p class="page-subtitle">Inspect, inject, and withdraw granular traffic-filtering rules (RFC 5575 / RFC 8955).</p>
      </div>
      <div class="header-actions">
        <button
          class="btn btn-primary"
          :disabled="!authStore.canEdit"
          :title="authStore.canEdit ? 'Create a new BGP Flowspec rule' : 'Operator or Admin role required to create rules'"
          @click="showCreateModal = true"
        >
          <Plus :size="18" /> Create Flowspec Rule
        </button>
      </div>
    </div>

    <!-- Rule Builder Modal Component -->
    <RuleBuilderModal
      v-if="showCreateModal"
      @close="showCreateModal = false"
      @created="flowspecStore.fetchRules()"
    />

    <!-- Filters Bar -->
    <div class="filters-bar card">
      <div class="filter-group">
        <Filter :size="16" class="filter-icon" />
        <span class="filter-label">Family:</span>
        <select v-model="selectedFamily" class="select-input">
          <option value="ALL">All Families</option>
          <option value="IPv4">IPv4 Flowspec</option>
          <option value="IPv6">IPv6 Flowspec</option>
        </select>
      </div>

      <div class="filter-group">
        <span class="filter-label">Action:</span>
        <select v-model="selectedAction" class="select-input">
          <option value="ALL">All Actions</option>
          <option value="Drop">Drop (Discard)</option>
          <option value="Shape">Rate-limit / Shape</option>
          <option value="Redirect">Redirect VRF/IP</option>
          <option value="Mark">Mark DSCP</option>
        </select>
      </div>

      <div class="results-count">
        Showing {{ filteredRules.length }} of {{ flowspecStore.rules.length }} rules
      </div>
    </div>

    <!-- Rules Table Card -->
    <div class="card">
      <div v-if="flowspecStore.loading" class="loading-state">Loading rules from database...</div>
      <div v-else-if="filteredRules.length === 0" class="empty-state">
        No Flowspec rules match the selected criteria.
      </div>
      <table v-else class="data-table">
        <thead>
          <tr>
            <th>Rule ID & Name</th>
            <th>Family</th>
            <th>Match Criteria</th>
            <th>Action</th>
            <th>RIB State</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="rule in filteredRules" :key="rule.id">
            <td>
              <div class="font-medium text-white">{{ rule.name || `Rule #${rule.id}` }}</div>
              <div class="text-xs text-muted font-mono" v-if="rule.description">{{ rule.description }}</div>
            </td>
            <td>
              <span class="badge badge-info">{{ rule.addr_fam }}</span>
            </td>
            <td>
              <div class="criteria-list font-mono text-xs">
                <span v-if="rule.dst_prefix" class="criteria-pill">dst: {{ rule.dst_prefix }}</span>
                <span v-if="rule.src_prefix" class="criteria-pill">src: {{ rule.src_prefix }}</span>
                <span v-if="rule.proto_number" class="criteria-pill">proto: {{ rule.proto_number }}</span>
                <span v-if="rule.port" class="criteria-pill">port: {{ rule.port }}</span>
                <span v-if="rule.src_port" class="criteria-pill">src_port: {{ rule.src_port }}</span>
                <span v-if="rule.dst_port" class="criteria-pill">dst_port: {{ rule.dst_port }}</span>
                <span v-if="rule.tcp_flags" class="criteria-pill">flags: {{ rule.tcp_flags }}</span>
                <span v-if="rule.dscp" class="criteria-pill">dscp: {{ rule.dscp }}</span>
              </div>
            </td>
            <td>
              <span class="badge" :class="rule.action === 'Drop' ? 'badge-danger' : 'badge-warning'">
                {{ rule.action }}
                <span v-if="rule.action_value" class="text-xs font-mono ml-1">({{ rule.action_value }})</span>
              </span>
            </td>
            <td>
              <StatusBadge
                :status="rule.is_active ? 'active' : 'inactive'"
                :label="rule.is_active ? 'Injected' : 'Withdrawn'"
              />
            </td>
            <td>
              <div class="action-buttons">
                <button
                  class="btn btn-secondary btn-icon"
                  :disabled="!authStore.canEdit"
                  :title="!authStore.canEdit ? 'Operator or Admin role required' : (rule.is_active ? 'Withdraw from BGP' : 'Inject into BGP')"
                  @click="flowspecStore.toggleRule(rule.id)"
                >
                  <Power :size="16" :class="{ 'text-green': rule.is_active, 'text-muted': !rule.is_active }" />
                </button>
                <button
                  class="btn btn-secondary btn-icon text-danger"
                  :disabled="!authStore.canEdit"
                  :title="!authStore.canEdit ? 'Operator or Admin role required' : 'Delete rule'"
                  @click="flowspecStore.deleteRule(rule.id)"
                >
                  <Trash2 :size="16" />
                </button>
              </div>
            </td>
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
.filters-bar {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 16px 20px;
  margin-bottom: 20px;
}
.filter-group {
  display: flex;
  align-items: center;
  gap: 10px;
}
.filter-icon {
  color: var(--color-text-muted);
}
.filter-label {
  font-size: 0.875rem;
  color: var(--color-text-muted);
}
.select-input {
  background-color: var(--color-bg);
  border: 1px solid var(--color-surface-border);
  color: var(--color-text-main);
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.875rem;
}
.results-count {
  margin-left: auto;
  font-size: 0.875rem;
  color: var(--color-text-muted);
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
.criteria-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.criteria-pill {
  background-color: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}
.action-buttons {
  display: flex;
  gap: 8px;
}
.btn-icon {
  padding: 6px;
}
.text-green { color: #34d399; }
.text-danger { color: #f87171; }
.loading-state, .empty-state {
  padding: 36px;
  text-align: center;
  color: var(--color-text-muted);
}
</style>
