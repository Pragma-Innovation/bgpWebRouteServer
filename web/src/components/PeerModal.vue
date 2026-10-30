<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useBgpStore, type BgpPeerConfig } from '../stores/bgpStore'
import { X, Network, Check, AlertCircle, Eye, EyeOff, ShieldCheck } from 'lucide-vue-next'

const props = defineProps<{
  show: boolean
  peerToEdit: BgpPeerConfig | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved'): void
}>()

const bgpStore = useBgpStore()

const availableFamilies = [
  { id: 'ipv4-unicast', label: 'IPv4 Unicast', desc: 'Standard IPv4 routing prefixes' },
  { id: 'ipv6-unicast', label: 'IPv6 Unicast', desc: 'Standard IPv6 routing prefixes' },
  { id: 'ipv4-flowspec', label: 'IPv4 Flowspec', desc: 'RFC 8955 IPv4 traffic filtering rules' },
  { id: 'ipv6-flowspec', label: 'IPv6 Flowspec', desc: 'RFC 8956 IPv6 traffic filtering rules' },
]

const form = ref<{
  neighbor_address: string
  peer_as: number
  description: string
  is_enabled: boolean
  multihop_enabled: boolean
  multihop_ttl: number
  md5_password: string
  passive_mode: boolean
  hold_time: number
  keepalive_interval: number
  families: string[]
}>({
  neighbor_address: '',
  peer_as: 65001,
  description: '',
  is_enabled: true,
  multihop_enabled: false,
  multihop_ttl: 64,
  md5_password: '',
  passive_mode: false,
  hold_time: 90,
  keepalive_interval: 30,
  families: ['ipv4-unicast', 'ipv4-flowspec'],
})

const showPassword = ref(false)
const errorMessage = ref<string | null>(null)
const successMessage = ref<string | null>(null)

const isEditMode = computed(() => !!props.peerToEdit)

// Detect whether session will be iBGP or eBGP based on global config ASN
const detectedSessionType = computed(() => {
  const localAsn = bgpStore.globalConfig?.local_as
  if (!localAsn || !form.value.peer_as) return null
  return form.value.peer_as === localAsn ? 'iBGP' : 'eBGP'
})

const detectedIpVersion = computed(() => {
  const addr = (form.value.neighbor_address || '').trim()
  if (!addr) return null
  return addr.includes(':') ? 'IPv6' : 'IPv4'
})

watch(
  () => props.show,
  (val) => {
    if (val) {
      errorMessage.value = null
      successMessage.value = null
      if (props.peerToEdit) {
        form.value = {
          neighbor_address: props.peerToEdit.neighbor_address || '',
          peer_as: props.peerToEdit.peer_as,
          description: props.peerToEdit.description || '',
          is_enabled: props.peerToEdit.is_enabled ?? true,
          multihop_enabled: props.peerToEdit.multihop_enabled ?? false,
          multihop_ttl: props.peerToEdit.multihop_ttl || 64,
          md5_password: props.peerToEdit.md5_password || '',
          passive_mode: props.peerToEdit.passive_mode ?? false,
          hold_time: props.peerToEdit.hold_time || 90,
          keepalive_interval: props.peerToEdit.keepalive_interval || 30,
          families: Array.isArray(props.peerToEdit.families) && props.peerToEdit.families.length > 0
            ? [...props.peerToEdit.families]
            : ['ipv4-unicast', 'ipv4-flowspec'],
        }
      } else {
        form.value = {
          neighbor_address: '',
          peer_as: bgpStore.globalConfig?.local_as || 65001,
          description: '',
          is_enabled: true,
          multihop_enabled: false,
          multihop_ttl: 64,
          md5_password: '',
          passive_mode: false,
          hold_time: 90,
          keepalive_interval: 30,
          families: ['ipv4-unicast', 'ipv4-flowspec'],
        }
      }
    }
  },
  { immediate: true }
)

function toggleFamily(famId: string) {
  const idx = form.value.families.indexOf(famId)
  if (idx > -1) {
    if (form.value.families.length > 1) {
      form.value.families.splice(idx, 1)
    }
  } else {
    form.value.families.push(famId)
  }
}

async function handleSubmit() {
  errorMessage.value = null
  successMessage.value = null

  const addr = form.value.neighbor_address.trim()
  if (!addr) {
    errorMessage.value = 'Neighbor IP address is required.'
    return
  }

  if (!form.value.peer_as || form.value.peer_as < 1 || form.value.peer_as > 4294967295) {
    errorMessage.value = 'Remote ASN must be between 1 and 4294967295.'
    return
  }

  if (form.value.families.length === 0) {
    errorMessage.value = 'At least one address family must be selected.'
    return
  }

  const payload: Partial<BgpPeerConfig> = {
    neighbor_address: addr,
    peer_as: Number(form.value.peer_as),
    description: form.value.description.trim(),
    is_enabled: form.value.is_enabled,
    multihop_enabled: form.value.multihop_enabled,
    multihop_ttl: Number(form.value.multihop_ttl) || 64,
    md5_password: form.value.md5_password.trim(),
    passive_mode: form.value.passive_mode,
    hold_time: Number(form.value.hold_time) || 90,
    keepalive_interval: Number(form.value.keepalive_interval) || 30,
    families: form.value.families,
  }

  try {
    if (isEditMode.value && props.peerToEdit?.id) {
      await bgpStore.updatePeerConfig(props.peerToEdit.id, payload)
      successMessage.value = `Peer ${addr} updated and synced with GoBGP!`
    } else {
      await bgpStore.createPeerConfig(payload)
      successMessage.value = `Peer ${addr} created and session initialized!`
    }
    setTimeout(() => {
      emit('saved')
      emit('close')
    }, 700)
  } catch (err: any) {
    errorMessage.value = err.message || 'Failed to save peer configuration'
  }
}
</script>

<template>
  <div v-if="show" class="modal-overlay" @click.self="emit('close')">
    <div class="modal-card">
      <div class="modal-header">
        <div class="modal-title-group">
          <div class="icon-bubble">
            <Network :size="20" class="text-primary" />
          </div>
          <div>
            <h2 class="modal-title">{{ isEditMode ? 'Edit BGP Peer' : 'Add BGP Peer' }}</h2>
            <p class="modal-subtitle">
              Configure BGP neighbor peering parameters, transport protocol, and capabilities.
            </p>
          </div>
        </div>
        <button class="close-btn" @click="emit('close')">
          <X :size="20" />
        </button>
      </div>

      <div class="modal-body">
        <div v-if="errorMessage" class="alert alert-danger">
          <AlertCircle :size="18" />
          <span>{{ errorMessage }}</span>
        </div>

        <div v-if="successMessage" class="alert alert-success">
          <Check :size="18" />
          <span>{{ successMessage }}</span>
        </div>

        <!-- IP Address & Remote ASN -->
        <div class="form-grid">
          <div class="form-group">
            <div class="label-with-badge">
              <label class="form-label">Neighbor Address *</label>
              <span v-if="detectedIpVersion" class="badge-mini font-mono">
                {{ detectedIpVersion }}
              </span>
            </div>
            <input
              v-model="form.neighbor_address"
              type="text"
              class="form-input font-mono"
              placeholder="e.g. 10.100.0.20 or 2001:db8::1"
              :disabled="isEditMode"
              required
            />
            <span class="field-hint">IPv4 or IPv6 address of the remote router.</span>
          </div>

          <div class="form-group">
            <div class="label-with-badge">
              <label class="form-label">Remote ASN *</label>
              <span
                v-if="detectedSessionType"
                :class="['badge-session', detectedSessionType === 'iBGP' ? 'badge-ibgp' : 'badge-ebgp']"
              >
                {{ detectedSessionType }}
              </span>
            </div>
            <input
              v-model.number="form.peer_as"
              type="number"
              min="1"
              max="4294967295"
              class="form-input font-mono"
              placeholder="e.g. 65001"
              required
            />
            <span class="field-hint">
              {{ detectedSessionType === 'iBGP' ? 'Internal peer (matches local ASN)' : 'External peer (eBGP)' }}
            </span>
          </div>
        </div>

        <!-- Description -->
        <div class="form-group">
          <label class="form-label">Description / Note</label>
          <input
            v-model="form.description"
            type="text"
            class="form-input"
            placeholder="e.g. Backbone Edge Router R1 (BIRD 3)"
          />
        </div>

        <!-- Session Status & Passive Flags -->
        <div class="section-box">
          <div class="flags-grid">
            <label class="toggle-label">
              <input type="checkbox" v-model="form.is_enabled" class="toggle-checkbox" />
              <span class="toggle-text">Session Enabled</span>
            </label>

            <label class="toggle-label">
              <input type="checkbox" v-model="form.passive_mode" class="toggle-checkbox" />
              <span class="toggle-text">Passive Mode (Listen Only)</span>
            </label>
          </div>
          <p class="section-hint">
            When <strong>Passive Mode</strong> is checked, Gabu waits for the remote neighbor to initiate the TCP handshake.
          </p>
        </div>

        <!-- Multi-Hop & MD5 Authentication -->
        <div class="section-box mt-3">
          <div class="checkbox-row">
            <label class="toggle-label">
              <input type="checkbox" v-model="form.multihop_enabled" class="toggle-checkbox" />
              <span class="toggle-text">Enable eBGP Multi-Hop</span>
            </label>
          </div>
          <p class="section-hint">
            Required when eBGP neighbor is reachable over multiple IP hops rather than a directly connected L2/L3 subnet.
          </p>

          <div v-if="form.multihop_enabled" class="form-group mt-2">
            <label class="form-label">Multi-Hop TTL (1 - 255)</label>
            <input
              v-model.number="form.multihop_ttl"
              type="number"
              min="1"
              max="255"
              class="form-input font-mono w-half"
              placeholder="64"
            />
          </div>

          <div class="divider-sub"></div>

          <div class="form-group mb-0">
            <div class="label-with-badge">
              <label class="form-label">TCP MD5 Password (RFC 2385)</label>
              <span v-if="form.md5_password" class="badge-mini text-green flex items-center gap-1">
                <ShieldCheck :size="12" /> Protected
              </span>
            </div>
            <div class="input-with-action">
              <input
                v-model="form.md5_password"
                :type="showPassword ? 'text' : 'password'"
                class="form-input font-mono"
                placeholder="Optional MD5 authentication key"
              />
              <button
                type="button"
                class="input-action-btn"
                @click="showPassword = !showPassword"
                title="Toggle visibility"
              >
                <EyeOff v-if="showPassword" :size="16" />
                <Eye v-else :size="16" />
              </button>
            </div>
            <span class="field-hint">Leave blank if no MD5 signature is configured on the remote router.</span>
          </div>
        </div>

        <!-- Address Families -->
        <div class="section-box mt-3">
          <div class="form-label mb-2">BGP Address Families (AFI / SAFI) *</div>
          <div class="families-grid">
            <div
              v-for="fam in availableFamilies"
              :key="fam.id"
              class="family-card"
              :class="{ selected: form.families.includes(fam.id) }"
              @click="toggleFamily(fam.id)"
            >
              <input
                type="checkbox"
                :checked="form.families.includes(fam.id)"
                class="toggle-checkbox"
                @click.stop
                @change="toggleFamily(fam.id)"
              />
              <div>
                <div class="fam-label font-mono">{{ fam.label }}</div>
                <div class="fam-desc">{{ fam.desc }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Timers -->
        <div class="section-box mt-3">
          <div class="form-label mb-2">BGP Timers</div>
          <div class="form-grid">
            <div class="form-group mb-0">
              <label class="form-label">Hold Time (sec)</label>
              <input
                v-model.number="form.hold_time"
                type="number"
                min="0"
                max="65535"
                class="form-input font-mono"
                placeholder="90"
              />
            </div>
            <div class="form-group mb-0">
              <label class="form-label">Keepalive Interval (sec)</label>
              <input
                v-model.number="form.keepalive_interval"
                type="number"
                min="0"
                max="65535"
                class="form-input font-mono"
                placeholder="30"
              />
            </div>
          </div>
          <span class="field-hint mt-2">Standard recommendation is keepalive = 1/3 of hold time.</span>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-secondary" @click="emit('close')" :disabled="bgpStore.savingPeer">
          Cancel
        </button>
        <button class="btn btn-primary" @click="handleSubmit" :disabled="bgpStore.savingPeer">
          <Check v-if="!bgpStore.savingPeer" :size="16" />
          <span>{{ bgpStore.savingPeer ? 'Saving Peer...' : isEditMode ? 'Update Peer' : 'Add Peer' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(11, 17, 32, 0.85);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 16px;
}

.modal-card {
  background-color: var(--color-surface);
  border: 1px solid var(--color-surface-border);
  border-radius: 12px;
  width: 100%;
  max-width: 660px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
  overflow: hidden;
  animation: fadeInScale 0.15s ease-out;
}

@keyframes fadeInScale {
  from {
    opacity: 0;
    transform: scale(0.97);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-surface-border);
  background-color: rgba(255, 255, 255, 0.02);
}

.modal-title-group {
  display: flex;
  align-items: center;
  gap: 14px;
}

.icon-bubble {
  background-color: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.3);
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: #fff;
}

.modal-subtitle {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-top: 2px;
}

.close-btn {
  background: transparent;
  color: var(--color-text-dim);
  padding: 6px;
  border-radius: 6px;
  transition: all 0.2s;
}

.close-btn:hover {
  color: #fff;
  background-color: var(--color-surface-hover);
}

.modal-body {
  padding: 24px;
  max-height: 72vh;
  overflow-y: auto;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-group {
  margin-bottom: 16px;
}

.mb-0 {
  margin-bottom: 0;
}

.label-with-badge {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.form-label {
  display: block;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--color-text-muted);
}

.badge-mini {
  font-size: 0.7rem;
  background-color: #1e293b;
  border: 1px solid #334155;
  color: #94a3b8;
  padding: 2px 6px;
  border-radius: 4px;
}

.badge-session {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 9999px;
  text-transform: uppercase;
}

.badge-ibgp {
  background-color: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.badge-ebgp {
  background-color: rgba(168, 85, 247, 0.15);
  color: #c084fc;
  border: 1px solid rgba(168, 85, 247, 0.3);
}

.form-input {
  width: 100%;
  background-color: #0b1120;
  border: 1px solid var(--color-surface-border);
  color: #fff;
  padding: 9px 12px;
  border-radius: 6px;
  font-size: 0.9rem;
  transition: border-color 0.2s;
}

.form-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.w-half {
  width: 50%;
}

.field-hint {
  display: block;
  font-size: 0.725rem;
  color: var(--color-text-dim);
  margin-top: 4px;
}

.section-box {
  background-color: rgba(11, 17, 32, 0.5);
  border: 1px solid var(--color-surface-border);
  border-radius: 8px;
  padding: 14px;
}

.flags-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.toggle-checkbox {
  width: 16px;
  height: 16px;
  accent-color: var(--color-primary);
  cursor: pointer;
}

.toggle-text {
  font-size: 0.85rem;
  font-weight: 500;
  color: #fff;
}

.section-hint {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-top: 6px;
  line-height: 1.4;
}

.divider-sub {
  height: 1px;
  background-color: rgba(255, 255, 255, 0.05);
  margin: 12px 0;
}

.input-with-action {
  position: relative;
  display: flex;
  align-items: center;
}

.input-action-btn {
  position: absolute;
  right: 8px;
  background: transparent;
  color: var(--color-text-dim);
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
}

.input-action-btn:hover {
  color: #fff;
}

.families-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 8px;
}

.family-card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--color-surface-border);
  border-radius: 6px;
  background-color: #0b1120;
  cursor: pointer;
  transition: all 0.2s;
}

.family-card:hover {
  border-color: #475569;
}

.family-card.selected {
  border-color: var(--color-primary);
  background-color: rgba(59, 130, 246, 0.08);
}

.fam-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #fff;
}

.fam-desc {
  font-size: 0.725rem;
  color: var(--color-text-muted);
  margin-top: 2px;
}

.mt-2 {
  margin-top: 8px;
}

.mt-3 {
  margin-top: 12px;
}

.mb-2 {
  margin-bottom: 8px;
}

.text-green {
  color: #34d399;
}

.alert {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 8px;
  font-size: 0.85rem;
  margin-bottom: 16px;
}

.alert-danger {
  background-color: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #f87171;
}

.alert-success {
  background-color: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #34d399;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--color-surface-border);
  background-color: rgba(255, 255, 255, 0.01);
}
</style>
