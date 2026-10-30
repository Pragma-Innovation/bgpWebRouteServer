<script setup lang="ts">
withDefaults(
  defineProps<{
    size?: number
    className?: string
  }>(),
  {
    size: 24,
    className: '',
  }
)
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    :class="className"
  >
    <defs>
      <!-- Gradient for the outer ring -->
      <linearGradient id="gabu-ring" x1="2" y1="2" x2="30" y2="30" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stop-color="#38bdf8" />
        <stop offset="50%" stop-color="#3b82f6" />
        <stop offset="100%" stop-color="#6366f1" />
      </linearGradient>

      <!-- Gradient for Route Server Core -->
      <radialGradient id="gabu-core" cx="16" cy="16" r="4" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stop-color="#67e8f9" />
        <stop offset="100%" stop-color="#0284c7" />
      </radialGradient>
    </defs>

    <!-- Outer Router Boundary Ring -->
    <circle
      cx="16"
      cy="16"
      r="13"
      stroke="url(#gabu-ring)"
      stroke-width="1.75"
      stroke-linecap="round"
      stroke-dasharray="2 1.5"
      opacity="0.85"
    />

    <!-- Diagonal cross peering mesh links -->
    <line x1="8" y1="8" x2="24" y2="24" stroke="#3b82f6" stroke-width="1" stroke-opacity="0.3" />
    <line x1="24" y1="8" x2="8" y2="24" stroke="#3b82f6" stroke-width="1" stroke-opacity="0.3" />

    <!-- 4 Cardinal BGP Routing Arrows (2 Inward, 2 Outward) -->
    <!-- North: Inward update to Route Server -->
    <path
      d="M16 5V11M16 11L13.5 8.5M16 11L18.5 8.5"
      stroke="#38bdf8"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    />

    <!-- South: Outward announcement from Route Server -->
    <path
      d="M16 21V27M16 27L13.5 24.5M16 27L18.5 24.5"
      stroke="#818cf8"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    />

    <!-- West: Outward announcement from Route Server -->
    <path
      d="M11 16H5M5 16L7.5 13.5M5 16L7.5 18.5"
      stroke="#818cf8"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    />

    <!-- East: Inward update to Route Server -->
    <path
      d="M27 16H21M21 16L23.5 13.5M21 16L23.5 18.5"
      stroke="#38bdf8"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    />

    <!-- Central Route Server Engine Node -->
    <circle cx="16" cy="16" r="3.25" fill="url(#gabu-core)" stroke="#ffffff" stroke-width="1.25" />

    <!-- Cardinal Peering Node Endpoints -->
    <circle cx="16" cy="3.5" r="1.5" fill="#38bdf8" />
    <circle cx="16" cy="28.5" r="1.5" fill="#818cf8" />
    <circle cx="3.5" cy="16" r="1.5" fill="#818cf8" />
    <circle cx="28.5" cy="16" r="1.5" fill="#38bdf8" />
  </svg>
</template>
