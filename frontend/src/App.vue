<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppIcon from './components/AppIcon.vue'
import StationPicker from './components/StationPicker.vue'
import StationMap from './components/StationMap.vue'
import ComparisonChart from './components/ComparisonChart.vue'
import ObservationTable from './components/ObservationTable.vue'
import { displayObservations, isNumber, numberText, rainText, timeText } from './weather.js'

const observations = ref([])
const meta = ref({})
const loading = ref(false)
const loaded = ref(false)
const error = ref('')
const refreshWarning = ref('')
const county = ref('')
const station = ref('')
const selectedId = ref('')
let controller
const counties = computed(() =>
  [...new Set(observations.value.map((row) => row.county_name).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, 'zh-Hant'),
  ),
)
const countyStations = computed(() =>
  observations.value
    .filter((row) => !county.value || row.county_name === county.value)
    .sort((a, b) => a.station_name.localeCompare(b.station_name, 'zh-Hant')),
)
const filtered = computed(() =>
  countyStations.value.filter((row) => !station.value || row.station_id === station.value),
)
const selected = computed(
  () => filtered.value.find((row) => row.station_id === selectedId.value) || filtered.value[0],
)
const temperatures = computed(() => filtered.value.map((row) => row.temperature).filter(isNumber))
const average = computed(() =>
  temperatures.value.length
    ? temperatures.value.reduce((a, b) => a + b, 0) / temperatures.value.length
    : null,
)
const rainy = computed(
  () =>
    filtered.value.filter(
      (row) =>
        (isNumber(row.precipitation) && row.precipitation > 0) ||
        row.precipitation_status === 'trace',
    ).length,
)
const missingRain = computed(
  () => filtered.value.filter((row) => !isNumber(row.precipitation)).length,
)
const invalidRain = computed(
  () => filtered.value.filter((row) => row.precipitation_status === 'invalid').length,
)
watch(county, () => {
  station.value = ''
})
watch(filtered, (rows) => {
  if (!rows.some((row) => row.station_id === selectedId.value))
    selectedId.value = rows[0]?.station_id || ''
})

function validatePayload(payload) {
  if (
    !payload ||
    !Array.isArray(payload.data) ||
    !payload.meta ||
    payload.meta.count !== payload.data.length
  )
    throw new Error('Invalid payload')
  const ids = new Set()
  for (const row of payload.data) {
    if (
      !row ||
      typeof row.station_id !== 'string' ||
      typeof row.station_name !== 'string' ||
      !Number.isFinite(Date.parse(row.observed_at)) ||
      ids.has(row.station_id)
    )
      throw new Error('Invalid observation')
    ids.add(row.station_id)
    for (const key of [
      'temperature',
      'humidity',
      'pressure',
      'precipitation',
      'wind_speed',
      'latitude',
      'longitude',
    ]) {
      if (row[key] !== null && !isNumber(row[key])) throw new Error('Invalid value')
    }
  }
}
async function reload() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 20000)
  try {
    const response = await fetch('/api/observations', {
      signal: controller.signal,
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    })
    if (!response.ok) throw new Error('Request failed')
    const payload = await response.json()
    validatePayload(payload)
    observations.value = displayObservations(payload.data)
    meta.value = payload.meta
    // 只在成功讀取後更新警告；讀取失敗時保留上次資料與更新狀態。
    refreshWarning.value =
      typeof payload.warning?.message === 'string'
        ? payload.data.length
          ? payload.warning.message
          : '更新失敗，目前尚無可顯示的觀測資料。'
        : ''
    loaded.value = true
    if (county.value && !counties.value.includes(county.value)) county.value = ''
    if (station.value && !countyStations.value.some((row) => row.station_id === station.value))
      station.value = ''
  } catch {
    error.value = loaded.value
      ? '重新讀取失敗，保留上次成功載入的觀測資料與時間。請稍後再試。'
      : '觀測資料暫時無法讀取，請稍後重試。'
  } finally {
    clearTimeout(timeout)
    loading.value = false
  }
}
function resetFilters() {
  county.value = ''
  station.value = ''
}
onMounted(reload)
onBeforeUnmount(() => controller?.abort())
</script>
<template>
  <main class="dashboard">
    <header class="dashboard-header">
      <div class="brand-mark"><AppIcon name="wind" /></div>
      <div class="header-copy">
        <div class="eyebrow">TAIWAN WEATHER OBSERVATIONS</div>
        <div class="title-line">
          <h1>臺灣氣象觀測</h1>
          <span class="snapshot-badge"><i></i>觀測資料快照</span>
        </div>
        <p>從測站觀測，了解此刻的臺灣天氣。</p>
      </div>
      <button class="reload-button" :disabled="loading" @click="reload">
        <AppIcon name="refresh" :class="{ spinning: loading }" />{{
          loading ? '讀取中…' : '重新讀取'
        }}
      </button>
    </header>
    <div class="time-strip">
      <span
        ><AppIcon name="clock" />最新觀測
        <strong>{{ timeText(meta.latest_observed_at) }}</strong></span
      ><span
        >資料擷取 <strong>{{ timeText(meta.latest_fetched_at) }}</strong></span
      ><span class="timezone">臺灣時間 UTC+8 · 資料來源：中央氣象署</span>
    </div>
    <div v-if="error" class="status-message error-message" role="alert">
      <span>{{ error }}</span
      ><button class="subtle-button" :disabled="loading" @click="reload">重試</button>
    </div>
    <div
      v-if="refreshWarning"
      class="status-message error-message refresh-warning"
      role="status"
    >
      <div class="refresh-warning-copy">
        <strong>最近一次資料更新失敗</strong>
        <p>{{ refreshWarning }}</p>
        <p class="footnote">
          最近更新嘗試：{{ timeText(meta.refresh?.attempted_at) }}
          <template v-if="meta.refresh?.last_success_at">
            · 上次更新成功：{{ timeText(meta.refresh.last_success_at) }}
          </template>
        </p>
      </div>
    </div>
    <div v-if="loading && !loaded" class="status-message" role="status">正在讀取測站觀測資料…</div>
    <template v-if="loaded">
      <section class="summary-grid" aria-label="觀測摘要">
        <article class="summary-card">
          <div><span>目前顯示測站</span><AppIcon name="pin" /></div>
          <strong>{{ filtered.length }}<small>站</small></strong>
          <p>全部 {{ observations.length }} 站{{ county || station ? ' · 已套用篩選' : '' }}</p>
        </article>
        <article class="summary-card">
          <div><span>有效氣溫觀測</span><AppIcon name="check" /></div>
          <strong>{{ temperatures.length }}<small>站</small></strong>
          <p>{{ filtered.length - temperatures.length }} 站氣溫缺值</p>
        </article>
        <article class="summary-card">
          <div><span>測站平均氣溫</span><AppIcon name="thermometer" /></div>
          <strong>{{ numberText(average) }}<small>°C</small></strong>
          <p>有效測站的未加權平均</p>
        </article>
        <article class="summary-card">
          <div><span>有降雨測站</span><AppIcon name="drop" /></div>
          <strong>{{ rainy }}<small>站</small></strong>
          <p>含雨跡 · {{ missingRain }} 站降雨缺值</p>
        </article>
      </section>
      <section class="panel filter-panel" aria-label="測站篩選">
        <label class="county-field"
          ><span class="field-label">縣市</span
          ><select v-model="county" aria-label="縣市">
            <option value="">全部縣市</option>
            <option v-for="name in counties" :key="name" :value="name">{{ name }}</option>
          </select></label
        >
        <StationPicker v-model="station" :stations="countyStations" />
        <button
          class="subtle-button clear-button"
          :disabled="!county && !station"
          @click="resetFilters"
        >
          <AppIcon name="close" />清除篩選
        </button>
        <span class="filter-result" aria-live="polite"
          >找到 <strong>{{ filtered.length }}</strong> 站</span
        >
      </section>
      <div v-if="!observations.length" class="status-message" role="status">
        目前尚無觀測資料。可以稍後重新讀取。
      </div>
      <div v-if="invalidRain" class="status-message" role="status">
        {{ invalidRain }} 站降雨值異常，顯示為「—（異常）」並排除降雨計算。
      </div>
      <div class="visual-grid" :aria-busy="loading">
        <StationMap
          :stations="filtered"
          :national="!county && !station"
          :selected-id="selected?.station_id || ''"
          @select="selectedId = $event"
        >
          <div v-if="selected" class="station-detail" aria-live="polite">
            <div class="detail-header">
              <div>
                <h3>
                  {{ selected.station_name }}<span>{{ selected.station_id }}</span>
                </h3>
                <p>
                  {{ selected.county_name || '—' }} · {{ selected.town_name || '—' }} · 海拔
                  {{ numberText(selected.altitude, 0) }} m
                </p>
              </div>
              <strong>{{ numberText(selected.temperature) }}<small>°C</small></strong>
            </div>
            <div class="detail-values">
              <span
                >相對濕度 <b>{{ numberText(selected.humidity, 0) }} %</b></span
              ><span
                >累積降雨 <b>{{ rainText(selected) }} mm</b></span
              ><span
                >風速 <b>{{ numberText(selected.wind_speed) }} m/s</b></span
              >
            </div>
            <p class="footnote">
              觀測 {{ timeText(selected.observed_at) }} · 擷取 {{ timeText(selected.fetched_at) }}
            </p>
          </div>
          <div v-else class="station-detail empty-state">選擇測站以查看觀測詳情</div>
        </StationMap>
        <ComparisonChart
          :stations="filtered"
          :selected-id="selected?.station_id || ''"
          @select="selectedId = $event"
        />
      </div>
      <ObservationTable
        :stations="filtered"
        :selected-id="selected?.station_id || ''"
        @select="selectedId = $event"
      />
    </template>
    <footer class="dashboard-footer">
      <span>中央氣象署 O-A0003-001 · 自動氣象站觀測</span
      ><span>降雨為當日累積值 ·「—」代表缺值 · 重新讀取會查詢已保存資料</span>
    </footer>
  </main>
</template>
