<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'
const props = defineProps({ modelValue: String, stations: Array })
const emit = defineEmits(['update:modelValue'])
const root = ref(null)
const search = ref(null)
const open = ref(false)
const query = ref('')
const active = ref(0)
const selected = computed(() => props.stations.find((row) => row.station_id === props.modelValue))
const options = computed(() => {
  const text = query.value.trim().toLowerCase()
  return props.stations.filter((row) =>
    `${row.station_name} ${row.station_id}`.toLowerCase().includes(text),
  )
})
function choose(id) {
  emit('update:modelValue', id)
  open.value = false
  query.value = ''
  root.value.querySelector('button').focus()
}
function closeOutside(event) {
  if (!root.value?.contains(event.target)) open.value = false
}
function keydown(event) {
  if (event.key === 'Escape') {
    open.value = false
    root.value.querySelector('button').focus()
  }
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    active.value = Math.max(
      0,
      Math.min(options.value.length, active.value + (event.key === 'ArrowDown' ? 1 : -1)),
    )
    root.value
      .querySelector(`#station-option-${active.value}`)
      ?.scrollIntoView({ block: 'nearest' })
  }
  if (event.key === 'Enter') {
    event.preventDefault()
    choose(active.value === 0 ? '' : options.value[active.value - 1]?.station_id || '')
  }
}
watch(query, () => {
  active.value = 0
})
watch(open, (value) => {
  if (value) {
    query.value = ''
    active.value = 0
    requestAnimationFrame(() => search.value?.focus())
  }
})
onMounted(() => document.addEventListener('pointerdown', closeOutside))
onBeforeUnmount(() => document.removeEventListener('pointerdown', closeOutside))
</script>
<template>
  <div
    ref="root"
    class="station-picker"
    @keydown="keydown"
    @focusout="
      (event) => {
        if (!root.contains(event.relatedTarget)) open = false
      }
    "
  >
    <span class="field-label" id="station-label">測站名稱 / 代碼</span>
    <button
      class="picker-trigger"
      aria-labelledby="station-label station-current"
      aria-haspopup="listbox"
      :aria-expanded="open"
      aria-controls="station-options"
      @click="open = !open"
    >
      <span id="station-current">{{
        selected ? `${selected.station_name} · ${selected.station_id}` : '全部測站'
      }}</span
      ><AppIcon name="chevron" />
    </button>
    <div v-if="open" class="picker-menu">
      <div class="picker-search">
        <AppIcon name="search" /><input
          ref="search"
          v-model="query"
          role="combobox"
          aria-label="搜尋測站名稱或代碼"
          aria-autocomplete="list"
          aria-controls="station-options"
          :aria-expanded="open"
          :aria-activedescendant="`station-option-${active}`"
          placeholder="輸入測站名稱或代碼"
        />
      </div>
      <ul id="station-options" role="listbox" aria-label="測站" class="picker-options">
        <li
          id="station-option-0"
          role="option"
          @pointerdown.prevent
          :aria-selected="!modelValue"
          :class="{ active: active === 0 }"
          @pointermove="active = 0"
          @click="choose('')"
        >
          <span>全部測站</span><AppIcon v-if="!modelValue" name="check" />
        </li>
        <li
          v-for="(row, i) in options"
          :id="`station-option-${i + 1}`"
          :key="row.station_id"
          role="option"
          @pointerdown.prevent
          :aria-selected="modelValue === row.station_id"
          :class="{ active: active === i + 1 }"
          @pointermove="active = i + 1"
          @click="choose(row.station_id)"
        >
          <span
            >{{ row.station_name }}<small>{{ row.station_id }} · {{ row.county_name }}</small></span
          ><AppIcon v-if="modelValue === row.station_id" name="check" />
        </li>
      </ul>
      <p v-if="!options.length" class="picker-empty">找不到符合的測站</p>
    </div>
  </div>
</template>
