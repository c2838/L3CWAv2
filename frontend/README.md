# 臺灣氣象觀測前端

Vue 3＋Vite，透過同站 `GET /api/observations` 顯示已保存的中央氣象署測站資料。地圖使用 Leaflet 1.9.4 與 OpenStreetMap 底圖。

## 本機啟動

在專案根目錄啟動既有的唯讀 API：

```sh
.venv/bin/python -B -m api.observations
```

另一個終端在專案根目錄啟動前端：

```sh
npm --prefix frontend run dev
```

開啟 Vite 顯示的本機網址。開發代理預設將 `/api` 轉送至 `http://127.0.0.1:8000`；需要測試其他本機 API 時可用 `WEATHER_API_TARGET` 設定代理目的地。此變數僅由 Vite 設定讀取。

正式建置：

```sh
npm --prefix frontend run build
```

`vite preview` 只預覽靜態產物，沒有此開發代理；正式部署的同站 Python API 路由於後續 Vercel 階段設定。

## 操作與資料呈現

- 縣市與可搜尋的測站下拉選單共同篩選摘要、地圖、比較圖與表格。
- 地圖支援縮放、拖曳、測站名稱提示、氣溫／降雨色階；點選測站查看詳情。初始聚焦臺灣本島，「顯示全部」涵蓋篩選後的所有座標，包括遠端島嶼。
- 比較圖每頁 8 站，支援氣溫、濕度、風速、累積降雨及由高／低排序；刻度以整個篩選集合計算，不隨頁碼改變。
- 表格每頁 10 站，預設氣溫降序。除測站名稱／位置外，各顯示欄位可升降排序；缺值始終放在最後。
- 時間使用 `Asia/Taipei`；降雨是當日累積值，雨跡與 6 小時無雨保留原狀態標示。
- API 中的負降雨值由前端顯示為「—（異常）」並排除數值計算；API／資料庫原值不改動，來源轉換仍需追查。
- 初次失敗顯示重試；重新讀取失敗保留上次成功資料與時間。空資料及等待狀態均有提示。
- 「重新讀取」僅呼叫 GET，不觸發 `POST /api/refresh`。前端沒有 CWA、Turso 或管理更新憑證。

## 元件

- `App.vue`：資料讀取、驗證、篩選、摘要與選站狀態。
- `StationPicker.vue`：搜尋、下拉選站與鍵盤操作。
- `StationMap.vue`：Leaflet 地圖、測站提示與色階。
- `ComparisonChart.vue`：比較圖及分頁。
- `ObservationTable.vue`：表格欄位排序及分頁。
- `PageControls.vue`：共用頁碼控制。
- `weather.js`：數值／時間格式、缺值排序、長條比例與降雨顯示規則。

OpenStreetMap 底圖需要網路，地圖保留來源標示；底圖讀取失敗時提供提示，測站圓點仍可查看。底圖使用遵循 [OpenStreetMap Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/)。
