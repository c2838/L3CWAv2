<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { isNumber, metricColor, metricText, metrics } from '../weather.js'
import AppIcon from './AppIcon.vue'
const props = defineProps({ stations: Array, selectedId: String, national: Boolean })
const emit = defineEmits(['select'])
const element = ref(null)
const mode = ref('temperature')
const tileError = ref(false)
const invalidCount = computed(
  () =>
    props.stations.filter(
      (row) =>
        !isNumber(row.latitude) ||
        !isNumber(row.longitude) ||
        Math.abs(row.latitude) > 90 ||
        Math.abs(row.longitude) > 180,
    ).length,
)
const legend = computed(() =>
  mode.value === 'temperature'
    ? [
        ['#6189c3', '< 10'],
        ['#69b8bd', '10–20'],
        ['#e5c675', '20–25'],
        ['#e79a67', '25–30'],
        ['#d66a64', '≥ 30'],
      ]
    : [
        ['#b9c7d6', '0'],
        ['#8bc9e7', '0–5'],
        ['#419bce', '5–20'],
        ['#2465b1', '20–50'],
        ['#6346a7', '≥ 50'],
      ],
)
let map, layer, resizeObserver
let markers = new Map()
function fitStations() {
  if (!map) return
  const points = [...markers.values()].map((marker) => marker.getLatLng())
  if (points.length)
    map.fitBounds(L.latLngBounds(points), {
      padding: [28, 28],
      maxZoom: points.length === 1 ? 11 : 8,
    })
  else map.setView([23.7, 120.8], 7)
}
function fitFiltered() {
  if (props.national)
    map.fitBounds(
      [
        [21.8, 119.1],
        [25.6, 122.2],
      ],
      { padding: [10, 10] },
    )
  else fitStations()
}
function draw() {
  if (!map) return
  layer.clearLayers()
  markers = new Map()
  for (const row of props.stations) {
    if (
      !isNumber(row.latitude) ||
      !isNumber(row.longitude) ||
      Math.abs(row.latitude) > 90 ||
      Math.abs(row.longitude) > 180
    )
      continue
    const selected = props.selectedId === row.station_id
    const marker = L.circleMarker([row.latitude, row.longitude], {
      radius: selected ? 8 : 5,
      color: selected ? '#193e72' : '#fff',
      weight: selected ? 3 : 1.2,
      fillColor: metricColor(row[mode.value], mode.value),
      fillOpacity: 0.92,
    })
    const tooltip = document.createElement('div')
    tooltip.textContent = `${row.station_name} · ${row.station_id}｜${metricText(row, mode.value)} ${isNumber(row[mode.value]) ? metrics[mode.value].unit : ''}`
    marker
      .bindTooltip(tooltip, { direction: 'top', offset: [0, -5] })
      .on('click', () => {
        emit('select', row.station_id)
        marker.openTooltip()
      })
      .addTo(layer)
    const path = marker.getElement()
    path.setAttribute('role', 'button')
    path.setAttribute('tabindex', '0')
    path.setAttribute('aria-label', `${row.station_name} ${row.station_id}，查看測站`)
    path.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault()
        emit('select', row.station_id)
      }
    })
    path.addEventListener('focus', () => marker.openTooltip())
    path.addEventListener('blur', () => marker.closeTooltip())
    markers.set(row.station_id, marker)
    if (selected) marker.bringToFront()
  }
}
onMounted(() => {
  map = L.map(element.value, { scrollWheelZoom: true, minZoom: 3, maxZoom: 18 }).setView(
    [23.7, 120.8],
    7,
  )
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution:
      '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  })
    .on('tileerror', () => {
      tileError.value = true
    })
    .addTo(map)
  layer = L.layerGroup().addTo(map)
  draw()
  fitFiltered()
  resizeObserver = new ResizeObserver(() => map.invalidateSize())
  resizeObserver.observe(element.value)
})
watch(
  () => props.stations,
  () => {
    draw()
    fitFiltered()
  },
)
watch(mode, draw)
watch(
  () => props.selectedId,
  () => {
    draw()
    const marker = markers.get(props.selectedId)
    if (marker && !map.getBounds().contains(marker.getLatLng())) map.panTo(marker.getLatLng())
  },
)
onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  map?.remove()
})
</script>
<template>
  <section class="panel map-panel" aria-labelledby="map-heading">
    <div class="panel-heading">
      <div>
        <h2 id="map-heading"><AppIcon name="pin" />測站分布</h2>
        <p>滾輪或雙指縮放 · 拖曳移動 · 點選測站</p>
      </div>
      <button class="subtle-button" @click="fitStations">顯示全部</button>
    </div>
    <div class="map-toolbar">
      <div class="segmented" role="group" aria-label="地圖顯示項目">
        <button :aria-pressed="mode === 'temperature'" @click="mode = 'temperature'">
          <AppIcon name="thermometer" />氣溫</button
        ><button :aria-pressed="mode === 'precipitation'" @click="mode = 'precipitation'">
          <AppIcon name="drop" />降雨
        </button>
      </div>
      <span>{{ stations.length - invalidCount }} 站位置</span>
    </div>
    <div ref="element" class="station-map" role="region" aria-label="可縮放的測站分布地圖"></div>
    <div class="map-legend">
      <span>{{ metrics[mode].unit }}</span
      ><span v-for="item in legend" :key="item[1]"
        ><i :style="{ background: item[0] }"></i>{{ item[1] }}</span
      ><span><i style="background: #9ca9b7"></i>缺值</span>
    </div>
    <p class="footnote">
      {{
        mode === 'precipitation'
          ? '當日累積降雨；雨跡小於可測量量，以 0 mm 色階呈現。'
          : '圓點顏色代表測站氣溫；移到圓點可查看名稱與數值。'
      }}
    </p>
    <p v-if="invalidCount" class="inline-notice">
      {{ invalidCount }} 站缺少有效座標，仍可在表格查看。
    </p>
    <p v-if="tileError" class="inline-notice" role="status">底圖暫時無法載入，測站位置仍可查看。</p>
    <slot />
  </section>
</template>
