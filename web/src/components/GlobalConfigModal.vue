<script setup lang="ts">
import { ref, watch } from 'vue'
import { useBgpStore, type BgpGlobalConfig } from '../stores/bgpStore'
import { X, Server, Check, AlertCircle } from 'lucide-vue-next'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved'): void
}>()

const bgpStore = useBgpStore()

const formData = ref<{
  local_as: number
  router_id: string
  listen_port: number
}>({
  local_as: 65000,
  router_id: '10.100.0.10',
  listen_port: 179,
})

const errorMessage = ref<string | null>(null)
const successMessage = ref<string | null>(null)

watch(
  () => props.show,
  (val) => {
    if (val && bgpStore.globalConfig) {
      formData.value = {
        local_as: bgpStore.globalConfig.local_as,
        router_id: bgpStore.globalConfig.router_id,
        listen_port: bgpStore.globalConfig.listen_port || 179,
      }
      errorMessage.value = null
      successMessage.value = null
    }
  },
  { immediate: true }
)

async function handleSubmit() {
  errorMessage.value = null
  successMessage.value = null

  if (!formData.value.local_as || formData.value.local_as < 1 || formData.value.local_as > 4294967295) {
    errorMessage.value = 'Local ASN must be a valid 16-bit or 32-bit ASN (1 to 4294967295).'
    return
  }

  if (!formData.value.router_id.trim()) {
    errorMessage.value = 'Router ID is required (IPv4 address format).'
    return
  }

  try {
    await bgpStore.updateGlobalConfig({
      local_as: Number(formData.value.local_as),
      router_id: formData.value.router_id.trim(),
      listen_port: Number(formData.value.listen_port) || 179,
    })
    successMessage.value = 'Global BGP parameters saved and applied to GoBGP!'
    setTimeout(() => {
      emit('saved')
      emit('close')
    }, 800)
  } catch (err: any) {
    errorMessage.value = err.message || 'Failed to update global BGP settings'
  }
}
</script>

<template>
  <div v-if="show" class="modal-overlay" @click.self="emit('close')">
    <div class="modal-card">
      <div class="modal-header">
        <div class="modal-title-group">
          <div class="icon-bubble">
            <Server :size="20" class="text-primary" />
          </div>
          <div>
            <h2 class="modal-title">Global Router Configuration</h2>
            <p class="modal-subtitle">Define local ASN, BGP Router ID, and TCP listening port.</p>
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

        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">Local ASN *</label>
            <input
              v-model.number="formData.local_as"
              type="number"
              min="1"
              max="4294967295"
              class="form-input font-mono"
              placeholder="e.g. 65000"
              required
            />
            <span class="field-hint">Autonomous System Number of this Gabu BGP speaker.</span>
          </div>

          <div class="form-group">
            <label class="form-label">Router ID *</label>
            <input
              v-model="formData.router_id"
              type="text"
              class="form-input font-mono"
              placeholder="e.g. 10.100.0.10"
              required
            />
            <span class="field-hint">Unique 32-bit identifier in dotted IPv4 notation.</span>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Listen Port</label>
          <input
            v-model.number="formData.listen_port"
            type="number"
            min="1"
            max="65535"
            class="form-input font-mono"
            placeholder="179"
          />
          <span class="field-hint">Standard TCP port is 179 for BGP transport.</span>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-secondary" @click="emit('close')" :disabled="bgpStore.savingGlobal">
          Cancel
        </button>
        <button class="btn btn-primary" @click="handleSubmit" :disabled="bgpStore.savingGlobal">
          <Check v-if="!bgpStore.savingGlobal" :size="16" />
          <span>{{ bgpStore.savingGlobal ? 'Saving Settings...' : 'Save & Sync Router' }}</span>
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
  max-width: 540px;
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
  max-height: 70vh;
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

.form-label {
  display: block;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--color-text-muted);
  margin-bottom: 6px;
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

.form-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.field-hint {
  display: block;
  font-size: 0.725rem;
  color: var(--color-text-dim);
  margin-top: 4px;
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
