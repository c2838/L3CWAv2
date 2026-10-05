<script setup>
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'
const props = defineProps({ page: Number, total: Number, size: Number, label: String })
const emit = defineEmits(['update:page'])
const pages = computed(() => Math.max(1, Math.ceil(props.total / props.size)))
</script>
<template>
  <nav class="pagination" :aria-label="label">
    <span
      >{{ total ? (page - 1) * size + 1 : 0 }}–{{ Math.min(page * size, total) }} /
      {{ total }} 站</span
    >
    <div class="page-actions">
      <button
        class="icon-button"
        :disabled="page <= 1"
        :aria-label="`${label}上一頁`"
        @click="emit('update:page', page - 1)"
      >
        <AppIcon name="left" />
      </button>
      <label class="page-select"
        ><span class="sr-only">{{ label }}頁碼</span
        ><select :value="page" @change="emit('update:page', Number($event.target.value))">
          <option v-for="n in pages" :key="n" :value="n">{{ n }} / {{ pages }}</option>
        </select></label
      >
      <button
        class="icon-button"
        :disabled="page >= pages"
        :aria-label="`${label}下一頁`"
        @click="emit('update:page', page + 1)"
      >
        <AppIcon name="right" />
      </button>
    </div>
  </nav>
</template>
