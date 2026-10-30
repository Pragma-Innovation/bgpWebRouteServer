<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useFlowspecStore, type FlowspecRule } from '../stores/flowspecStore'
import { X, ShieldAlert, Check } from 'lucide-vue-next'

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'created', rule: FlowspecRule): void
}>()

const flowspecStore = useFlowspecStore()
const isSubmitting = ref(false)
const errorMessage = ref<string | null>(null)

const form = reactive({
  name: '',
  description: '',
  addr_fam: 'IPv4' as 'IPv4' | 'IPv6',
  dst_prefix: '',
  src_prefix: '',
  proto_number: '',
  port: '',
  src_port: '',
  dst_port: '',
  tcp_flags: '',
  icmp_type: '',
  icmp_code: '',
  packet_len: '',
  dscp: '',
  ip_frag: '',
  action: 'Drop' as 'Drop' | 'Shape' | 'Redirect' | 'Mark',
  action_value: '',
})

// Quick protocol selector helper
function setProtocol(val: string) {
  form.proto_number = val
}

// TCP Flags quick toggles
const selectedFlags = ref<string[]>([])
const flagsNegate = ref(false)

function toggleFlag(flag: string) {
  if (selectedFlags.value.includes(flag)) {
    selectedFlags.value = selectedFlags.value.filter(f => f !== flag)
  } else {
    selectedFlags.value.push(flag)
  }
  updateTcpFlagsString()
}

function updateTcpFlagsString() {
  if (selectedFlags.value.length === 0) {
    form.tcp_flags = ''
  } else {
    const prefix = flagsNegate.value ? '=!' : '='
    form.tcp_flags = `${prefix}${selectedFlags.value.join('')}`
  }
}

const hasAtLeastOneMatch = computed(() => {
  return (
    form.dst_prefix.trim() !== '' ||
    form.src_prefix.trim() !== '' ||
    form.proto_number.trim() !== '' ||
    form.port.trim() !== '' ||
    form.src_port.trim() !== '' ||
    form.dst_port.trim() !== '' ||
    form.tcp_flags.trim() !== '' ||
    form.icmp_type.trim() !== ''
  )
})

async function submitForm() {
  if (!hasAtLeastOneMatch.value) {
    errorMessage.value = 'Please provide at least one match criteria (e.g. Destination Prefix, Protocol, or Port).'
    return
  }

  errorMessage.value = null
  isSubmitting.value = true

  try {
    const newRule = await flowspecStore.createRule({
      ...form,
      name: form.name.trim() || `Mitigation: ${form.action} ${form.dst_prefix || 'traffic'}`,
    })
    emit('created', newRule)
    emit('close')
  } catch (err: any) {
    errorMessage.value = err.response?.data ? JSON.stringify(err.response.data) : err.message
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <div class="modal-dialog">
      <!-- Modal Header -->
      <div class="modal-header">
        <div class="title-with-icon">
          <div class="icon-circle">
            <ShieldAlert :size="20" />
          </div>
          <div>
            <h3>Create BGP Flowspec Rule</h3>
            <p class="modal-subtitle">Define matching criteria and mitigation action for BGP propagation.</p>
          </div>
        </div>
        <button class="btn-close" @click="emit('close')">
          <X :size="20" />
        </button>
      </div>

      <!-- Error alert -->
      <div v-if="errorMessage" class="error-banner">
        {{ errorMessage }}
      </div>

      <!-- Form Body -->
      <form @submit.prevent="submitForm" class="modal-body">
        <!-- Family & Name -->
        <div class="form-row two-cols">
          <div class="form-group">
            <label>Address Family</label>
            <div class="segmented-control">
              <button
                type="button"
                :class="{ active: form.addr_fam === 'IPv4' }"
                @click="form.addr_fam = 'IPv4'"
              >
                IPv4 Flowspec
              </button>
              <button
                type="button"
                :class="{ active: form.addr_fam === 'IPv6' }"
                @click="form.addr_fam = 'IPv6'"
              >
                IPv6 Flowspec
              </button>
            </div>
          </div>

          <div class="form-group">
            <label>Rule Name (Optional)</label>
            <input
              v-model="form.name"
              type="text"
              class="form-control"
              placeholder="e.g. Mitigate NTP Amplification to VIP"
            />
          </div>
        </div>

        <!-- IP Prefixes -->
        <div class="form-row two-cols">
          <div class="form-group">
            <label>Destination Prefix / CIDR</label>
            <input
              v-model="form.dst_prefix"
              type="text"
              class="form-control font-mono"
              :placeholder="form.addr_fam === 'IPv4' ? '1.1.1.1/32' : '2001:db8::1/128'"
            />
            <span class="field-hint">Target victim IP or subnet</span>
          </div>

          <div class="form-group">
            <label>Source Prefix / CIDR</label>
            <input
              v-model="form.src_prefix"
              type="text"
              class="form-control font-mono"
              :placeholder="form.addr_fam === 'IPv4' ? '2.2.2.2/32' : '2001:db8:bad::/64'"
            />
            <span class="field-hint">Attacker IP or subnet (optional)</span>
          </div>
        </div>

        <!-- Protocol selection -->
        <div class="form-group">
          <label>IP Protocol Match</label>
          <div class="protocol-shortcuts">
            <button
              type="button"
              class="proto-chip"
              :class="{ active: form.proto_number === '' }"
              @click="setProtocol('')"
            >
              Any Protocol
            </button>
            <button
              type="button"
              class="proto-chip"
              :class="{ active: form.proto_number === '==6' }"
              @click="setProtocol('==6')"
            >
              TCP (==6)
            </button>
            <button
              type="button"
              class="proto-chip"
              :class="{ active: form.proto_number === '==17' }"
              @click="setProtocol('==17')"
            >
              UDP (==17)
            </button>
            <button
              type="button"
              class="proto-chip"
              :class="{ active: form.proto_number === '==1' }"
              @click="setProtocol('==1')"
            >
              ICMP (==1)
            </button>
          </div>
          <input
            v-model="form.proto_number"
            type="text"
            class="form-control font-mono mt-2"
            placeholder="Custom protocol match, e.g. ==6 ==17 or >50"
          />
        </div>

        <!-- Port matches -->
        <div class="form-row three-cols">
          <div class="form-group">
            <label>Port (Src or Dst)</label>
            <input
              v-model="form.port"
              type="text"
              class="form-control font-mono"
              placeholder="==8080 or >1024"
            />
          </div>
          <div class="form-group">
            <label>Source Port</label>
            <input
              v-model="form.src_port"
              type="text"
              class="form-control font-mono"
              placeholder="==80 or ==53"
            />
          </div>
          <div class="form-group">
            <label>Destination Port</label>
            <input
              v-model="form.dst_port"
              type="text"
              class="form-control font-mono"
              placeholder="==443 or ==389"
            />
          </div>
        </div>

        <!-- TCP Flags Selection -->
        <div class="form-group">
          <div class="label-with-checkbox">
            <label>TCP Flags Match</label>
            <label class="checkbox-label text-xs">
              <input type="checkbox" v-model="flagsNegate" @change="updateTcpFlagsString" />
              Negate flags (=!)
            </label>
          </div>
          <div class="flags-chips">
            <button
              v-for="flag in ['S', 'A', 'F', 'R', 'P', 'U']"
              :key="flag"
              type="button"
              class="flag-chip"
              :class="{ active: selectedFlags.includes(flag) }"
              @click="toggleFlag(flag)"
            >
              {{ flag === 'S' ? 'SYN (S)' : flag === 'A' ? 'ACK (A)' : flag === 'F' ? 'FIN (F)' : flag === 'R' ? 'RST (R)' : flag === 'P' ? 'PSH (P)' : 'URG (U)' }}
            </button>
          </div>
          <input
            v-model="form.tcp_flags"
            type="text"
            class="form-control font-mono mt-2"
            placeholder="e.g. =S or =SA or =!F"
          />
        </div>

        <!-- Action Selection -->
        <div class="action-box">
          <div class="form-row two-cols">
            <div class="form-group">
              <label>Mitigation Action</label>
              <select v-model="form.action" class="form-control">
                <option value="Drop">Drop (Discard packets)</option>
                <option value="Shape">Rate-limit / Shape (Traffic policing)</option>
                <option value="Redirect">Redirect (VRF / Route Target)</option>
                <option value="Mark">Mark (DSCP Remarking)</option>
              </select>
            </div>

            <div class="form-group" v-if="form.action !== 'Drop'">
              <label>Action Parameter</label>
              <input
                v-model="form.action_value"
                type="text"
                class="form-control font-mono"
                :placeholder="form.action === 'Shape' ? 'Rate in bytes/sec (e.g. 1000000)' : form.action === 'Redirect' ? 'Route Target (e.g. 10:200)' : 'DSCP value (e.g. 22)'"
              />
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="emit('close')">
            Cancel
          </button>
          <button type="submit" class="btn btn-primary" :disabled="isSubmitting">
            <Check :size="18" /> {{ isSubmitting ? 'Creating Rule...' : 'Create Flowspec Rule' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}
.modal-dialog {
  background-color: var(--color-surface);
  border: 1px solid var(--color-surface-border);
  border-radius: 14px;
  width: 100%;
  max-width: 680px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}
.modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-surface-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.title-with-icon {
  display: flex;
  align-items: center;
  gap: 12px;
}
.icon-circle {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background-color: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal-header h3 {
  font-size: 1.125rem;
  font-weight: 700;
  color: #ffffff;
}
.modal-subtitle {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}
.btn-close {
  background: none;
  color: var(--color-text-muted);
  padding: 6px;
  border-radius: 6px;
}
.btn-close:hover {
  background-color: rgba(255, 255, 255, 0.05);
  color: #ffffff;
}
.modal-body {
  padding: 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.form-row {
  display: grid;
  gap: 16px;
}
.two-cols { grid-template-columns: 1fr 1fr; }
.three-cols { grid-template-columns: 1fr 1fr 1fr; }

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-group label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-muted);
}
.form-control {
  background-color: #0b1120;
  border: 1px solid var(--color-surface-border);
  color: var(--color-text-main);
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 0.875rem;
  outline: none;
  transition: border-color 0.15s ease;
}
.form-control:focus {
  border-color: var(--color-primary);
}
.field-hint {
  font-size: 0.6875rem;
  color: var(--color-text-dim);
}
.segmented-control {
  display: flex;
  background-color: #0b1120;
  border-radius: 8px;
  padding: 3px;
  border: 1px solid var(--color-surface-border);
}
.segmented-control button {
  flex: 1;
  padding: 6px 12px;
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 6px;
  background: none;
  color: var(--color-text-muted);
}
.segmented-control button.active {
  background-color: var(--color-primary);
  color: #ffffff;
}
.protocol-shortcuts, .flags-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.proto-chip, .flag-chip {
  padding: 6px 12px;
  border-radius: 6px;
  background-color: #0b1120;
  border: 1px solid var(--color-surface-border);
  color: var(--color-text-muted);
  font-size: 0.75rem;
  font-weight: 500;
}
.proto-chip.active, .flag-chip.active {
  background-color: rgba(59, 130, 246, 0.2);
  border-color: var(--color-primary);
  color: #60a5fa;
  font-weight: 600;
}
.label-with-checkbox {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: var(--color-text-main);
}
.action-box {
  background-color: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--color-surface-border);
  border-radius: 10px;
  padding: 16px;
}
.error-banner {
  background-color: rgba(239, 68, 68, 0.15);
  border-bottom: 1px solid rgba(239, 68, 68, 0.3);
  color: #f87171;
  padding: 10px 24px;
  font-size: 0.8125rem;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-surface-border);
}
.mt-2 { margin-top: 8px; }
</style>
