<script setup>
import { computed, ref, watch } from 'vue'
import { numberText, rainText, sortObservations, timeText } from '../weather.js'
import AppIcon from './AppIcon.vue'
import PageControls from './PageControls.vue'
const props = defineProps({ stations: Array, selectedId: String })
const emit = defineEmits(['select'])
const key = ref('temperature')
const direction = ref('desc')
const page = ref(1)
const size = 10
const columns = [
  { key: 'temperature', label: '氣溫', unit: '°C' },
  { key: 'humidity', label: '濕度', unit: '%' },
  { key: 'precipitation', label: '累積降雨', unit: 'mm' },
  { key: 'wind_speed', label: '風速', unit: 'm/s' },
  { key: 'pressure', label: '氣壓', unit: 'hPa' },
  { key: 'observed_at', label: '觀測時間', unit: 'UTC+8' },
]
const rows = computed(() =>
  sortObservations(props.stations, key.value, direction.value).slice(
    (page.value - 1) * size,
    page.value * size,
  ),
)
function sort(column) {
  direction.value = key.value === column && direction.value === 'desc' ? 'asc' : 'desc'
  key.value = column
  page.value = 1
}
watch(
  () => props.stations,
  () => {
    page.value = 1
  },
)
function cell(row, column) {
  if (column === 'precipitation') return rainText(row)
  if (column === 'observed_at') return timeText(row[column])
  return numberText(row[column], column === 'humidity' ? 0 : 1)
}
</script>
<template>
  <section class="panel observation-panel" aria-labelledby="table-heading">
    <div class="panel-heading">
      <div>
        <h2 id="table-heading">觀測資料</h2>
        <p>點選測站查看詳情；點選欄位切換排序</p>
      </div>
      <span class="soft-badge">{{ stations.length }} 站</span>
    </div>
    <div class="table-scroll" role="region" aria-label="可水平捲動的觀測資料" tabindex="0">
      <table>
        <caption class="sr-only">
          測站觀測資料，預設氣溫降序，缺值排在最後
        </caption>
        <thead>
          <tr>
            <th scope="col">測站名稱 / 位置</th>
            <th
              v-for="column in columns"
              :key="column.key"
              scope="col"
              :aria-sort="
                key === column.key ? (direction === 'desc' ? 'descending' : 'ascending') : 'none'
              "
            >
              <button
                class="sort-button"
                :aria-label="`${column.label}排序`"
                @click="sort(column.key)"
              >
                <span
                  >{{ column.label }}<small>{{ column.unit }}</small></span
                ><span v-if="key === column.key" aria-hidden="true">{{
                  direction === 'desc' ? '↓' : '↑'
                }}</span
                ><AppIcon v-else name="sort" />
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in rows"
            :key="row.station_id"
            :class="{ selected: selectedId === row.station_id }"
          >
            <th scope="row">
              <button
                class="station-link"
                :aria-pressed="selectedId === row.station_id"
                @click="emit('select', row.station_id)"
              >
                <span
                  >{{ row.station_name }} <small>{{ row.station_id }}</small></span
                ><small>{{ row.county_name || '—' }} · {{ row.town_name || '—' }}</small>
              </button>
            </th>
            <td
              v-for="column in columns"
              :key="column.key"
              :class="{ 'temperature-cell': column.key === 'temperature' }"
            >
              {{ cell(row, column.key) }}
            </td>
          </tr>
          <tr v-if="!rows.length">
            <td colspan="7" class="empty-state">沒有符合篩選條件的觀測資料</td>
          </tr>
        </tbody>
      </table>
    </div>
    <PageControls v-model:page="page" :total="stations.length" :size="size" label="觀測表格" />
  </section>
</template>
