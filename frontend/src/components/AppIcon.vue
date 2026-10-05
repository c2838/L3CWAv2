<script setup>
defineProps({ name: String })
const paths = {
  wind: ['M3 8h12a3 3 0 1 0-3-3', 'M2 12h17a3 3 0 1 1-3 3', 'M4 16h6a3 3 0 1 1-3 3'],
  refresh: ['M20 7v5h-5', 'M4 17v-5h5', 'M6.1 6a8 8 0 0 1 13 2L20 12', 'M4 12l.9 4a8 8 0 0 0 13 2'],
  pin: ['M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z', 'M15 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0'],
  thermometer: ['M9 14V5a3 3 0 0 1 6 0v9a5 5 0 1 1-6 0Z', 'M12 9v9'],
  drop: ['M12 3s7 8 7 12a7 7 0 1 1-14 0c0-4 7-12 7-12Z'],
  chart: ['M4 3v17h17', 'M8 15V9', 'M13 15V5', 'M18 15v-4'],
  chevron: ['m6 9 6 6 6-6'],
  left: ['m14 6-6 6 6 6'],
  right: ['m10 6 6 6-6 6'],
  sort: ['m8 4-3 3-3-3', 'M5 4v16', 'm16 20 3-3 3 3', 'M19 4v16'],
  clock: ['M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0', 'M12 7v5l3 2'],
  search: ['M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0', 'm15 15 6 6'],
  check: ['m5 12 4 4L19 6'],
  close: ['m6 6 12 12', 'M18 6 6 18'],
}
</script>
<template>
  <svg
    class="icon"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path v-for="(d, i) in paths[name] || paths.pin" :key="i" :d="d" />
  </svg>
</template>
