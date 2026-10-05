<script setup>
import { computed, ref, watch } from 'vue'
import { metrics, sortObservations, barDomain, barStyle, metricText, isNumber } from '../weather.js'
import AppIcon from './AppIcon.vue'
import PageControls from './PageControls.vue'
const props = defineProps({ stations: Array, selectedId: String })
const emit = defineEmits(['select'])
const metric = ref('temperature')
const order = ref('desc')
const page = ref(1)
const size = 8
const sorted = computed(() => sortObservations(props.stations, metric.value, order.value))
const rows = computed(() => sorted.value.slice((page.value - 1) * size, page.value * size))
const domain = computed(() => barDomain(props.stations, metric.value))
const validCount = computed(
  () => props.stations.filter((row) => isNumber(row[metric.value])).length,
)
const zero = computed(() => `${(-domain.value[0] / (domain.value[1] - domain.value[0])) * 100}%`)
watch([() => props.stations, metric, order], () => {
  page.value = 1
})
</script>
<template>
  <section class="panel comparison-panel" aria-labelledby="comparison-heading">
    <div class="panel-heading">
      <div>
        <h2 id="comparison-heading"><AppIcon name="chart" />測站{{ metrics[metric].label }}比較</h2>
        <p>全部 {{ stations.length }} 站 · {{ validCount }} 站數值可用</p>
      </div>
    </div>
    <div class="chart-controls">
      <label
        ><span class="sr-only">比較項目</span
        ><select v-model="metric" aria-label="比較項目">
          <option v-for="(item, key) in metrics" :key="key" :value="key">
            {{ item.label }} ({{ item.unit }})
          </option>
        </select></label
      ><label
        ><span class="sr-only">比較排序</span
        ><select v-model="order" aria-label="比較排序">
          <option value="desc">由最高到最低</option>
          <option value="asc">由最低到最高</option>
        </select></label
      >
    </div>
    <div v-if="stations.length" class="bar-chart">
      <div class="bar-axis" aria-hidden="true">
        <span></span>
        <div>
          <span>{{ domain[0] }}</span
          ><span>{{ domain[1].toFixed(metric === 'humidity' ? 0 : 1) }}</span>
        </div>
        <span>{{ metrics[metric].unit }}</span>
      </div>
      <button
        v-for="row in rows"
        :key="row.station_id"
        class="bar-row"
        :class="{ selected: selectedId === row.station_id }"
        :aria-label="`${row.station_name}，${metrics[metric].label} ${metricText(row, metric)} ${metrics[metric].unit}，查看測站`"
        :aria-pressed="selectedId === row.station_id"
        @click="emit('select', row.station_id)"
      >
        <span class="bar-name"
          >{{ row.station_name }}<small>{{ row.station_id }}</small></span
        >
        <span class="bar-track"
          ><span class="bar-zero" :style="{ left: zero }"></span
          ><span class="bar-fill" :class="metric" :style="barStyle(row[metric], domain)"></span
        ></span>
        <span class="bar-value">{{ metricText(row, metric) }}</span>
      </button>
    </div>
    <div v-else class="empty-state">目前沒有符合條件的測站</div>
    <p class="footnote">缺值以「—」顯示並排在最後；每頁 8 站。降雨為當日累積量。</p>
    <PageControls v-model:page="page" :total="stations.length" :size="size" label="比較圖" />
  </section>
</template>
