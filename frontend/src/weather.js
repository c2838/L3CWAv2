export const metrics = {
  temperature: { label: '氣溫', unit: '°C', digits: 1 },
  humidity: { label: '相對濕度', unit: '%', digits: 0 },
  wind_speed: { label: '風速', unit: 'm/s', digits: 1 },
  precipitation: { label: '累積降雨', unit: 'mm', digits: 1 },
}

export const isNumber = (value) => typeof value === 'number' && Number.isFinite(value)
export const numberText = (value, digits = 1) => (isNumber(value) ? value.toFixed(digits) : '—')
export function displayObservations(rows) {
  return rows.map((row) =>
    isNumber(row.precipitation) && row.precipitation < 0
      ? { ...row, precipitation: null, precipitation_status: 'invalid' }
      : row,
  )
}
export function rainText(row) {
  if (row.precipitation_status === 'invalid') return '—（異常）'
  if (row.precipitation_status === 'trace') return '雨跡'
  if (row.precipitation_status === 'no_rain_6h') return '0.0 · 6h 無雨'
  return numberText(row.precipitation)
}
export function metricText(row, key) {
  return key === 'precipitation' ? rainText(row) : numberText(row[key], metrics[key].digits)
}
export function timeText(value, withDate = true) {
  if (!value || !Number.isFinite(Date.parse(value))) return '—'
  return new Intl.DateTimeFormat('zh-TW', {
    timeZone: 'Asia/Taipei',
    ...(withDate ? { month: '2-digit', day: '2-digit' } : {}),
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).format(new Date(value))
}

// 缺值不參與數值排序；升序、降序都放在最後，等值以代碼固定順序。
export function sortObservations(rows, key, direction = 'desc') {
  return [...rows].sort((a, b) => {
    const av = key === 'observed_at' ? Date.parse(a[key]) : a[key]
    const bv = key === 'observed_at' ? Date.parse(b[key]) : b[key]
    if (isNumber(av) !== isNumber(bv)) return isNumber(av) ? -1 : 1
    const delta = isNumber(av) ? av - bv : 0
    return (direction === 'asc' ? delta : -delta) || a.station_id.localeCompare(b.station_id)
  })
}

export function barDomain(rows, key) {
  const values = rows.map((row) => row[key]).filter(isNumber)
  return [Math.min(0, ...values), Math.max(1, ...values)]
}
export function barStyle(value, [min, max]) {
  if (!isNumber(value)) return { left: '0%', width: '0%' }
  const start = Math.min(0, value)
  return {
    left: `${((start - min) / (max - min)) * 100}%`,
    width: `${(Math.abs(value) / (max - min)) * 100}%`,
  }
}
export function metricColor(value, key) {
  if (!isNumber(value)) return '#9ca9b7'
  if (key === 'precipitation') {
    if (value <= 0) return '#b9c7d6'
    if (value < 5) return '#8bc9e7'
    if (value < 20) return '#419bce'
    if (value < 50) return '#2465b1'
    return '#6346a7'
  }
  if (value < 10) return '#6189c3'
  if (value < 20) return '#69b8bd'
  if (value < 25) return '#e5c675'
  if (value < 30) return '#e79a67'
  return '#d66a64'
}
