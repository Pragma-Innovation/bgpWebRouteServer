<script setup lang="ts">
defineProps<{
  status: 'online' | 'offline' | 'warning' | 'info' | string
  label?: string
}>()
</script>

<template>
  <span
    class="badge"
    :class="{
      'badge-success': status === 'online' || status === 'ESTABLISHED' || status === 'active',
      'badge-warning': status === 'warning' || status === 'ACTIVE' || status === 'CONNECT',
      'badge-danger': status === 'offline' || status === 'IDLE' || status === 'inactive',
      'badge-info': status === 'info'
    }"
  >
    <span class="dot" />
    {{ label || status }}
  </span>
</template>

<style scoped>
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: currentColor;
}
</style>
