# 數據導出功能設計思路 (Feature Export Design Thoughts)

## 1. 背景與目標

用戶需要在 `w2/db_query` 工具中實現在查詢後自動提示導出（CSV/JSON），並確保有手動導出按鈕。
目標是提升用戶體驗，防止用戶在執行複雜查詢後忘記保存數據。

## 2. 現狀分析

通過代碼審查 (`frontend/src/pages/Home.tsx`):

- **手動導出**: 目前 UI 中已經存在 "EXPORT CSV" 和 "EXPORT JSON" 按鈕（位於查詢結果卡片的右上角）。相應的邏輯 `handleExportCSV` 和 `handleExportJSON` 也已實現，包含大數據量 (>10,000 行) 的警告提示。
- **自動提示**: 目前沒有自動提示功能。

## 3. 設計方案

### 3.1 架構選擇

- **前端導出 (Client-side)**:
  - 優點：數據已經在前端內存中 (`queryResult`)，無需再次請求後端，響應快，減輕服務器壓力。
  - 缺點：受瀏覽器內存限制。但考慮到當前配置 `query_default_limit = 1000`，且已有大數據量警告，前端導出是合理的選擇。
  - 結論：沿用現有的前端導出邏輯，僅增加觸發機制。

### 3.2 交互流程

1. 用戶點擊 "EXECUTE" 或生成 SQL 執行。
2. 查詢成功，數據返回並渲染到表格。
3. **新增步驟**: 彈出一個 Modal 對話框，詢問 "是否需要導出查詢結果？"。
   - 選項 A: 導出為 CSV
   - 選項 B: 導出為 JSON
   - 選項 C: 取消 (關閉對話框)
4. 用戶選擇後執行相應導出函數。

### 3.3 組件設計

- **`Home.tsx`**:
  - 新增狀態 `showExportModal` (boolean)。
  - 修改 `handleExecuteQuery`: 在 `setQueryResult` 成功後，設置 `showExportModal(true)`。
  - 新增 `ExportPromptModal` 組件 (或直接使用 Ant Design `Modal`)：
    - Title: "查詢成功 (Query Success)"
    - Content: "查詢已完成，共 X 行數據。您需要導出結果嗎？"
    - Actions: [取消] [導出 CSV] [導出 JSON]

## 4. 權衡與細節

- **干擾性**: 每次查詢都彈窗可能會打擾用戶。
  - **優化**: 可以增加一個 "不再提示" 的 Checkbox (保存在 localStorage)，或者僅在數據量大於 10 行時提示。
  - **當前決策**: 根據需求 "自動提示"，暫不加入 "不再提示" 選項，保持簡單，確保用戶不會丟失數據。
- **樣式**: 使用與現有 UI 風格一致的 Ant Design 組件 (`#FFDE00` 黃色強調色等)。

## 5. 數據流

`Backend API` -> `Frontend (Home.tsx)` -> `queryResult State` -> `Export Modal` -> `Browser Download`
