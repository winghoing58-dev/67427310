# 實現計劃：自動導出提示功能 (0002-implementation-plan)

**日期**: 2026-02-03  
**依據文檔**: [0001-design.md](./0001-design.md)

## 1. 概述

本計劃旨在落實 "查詢後自動提示導出" 功能。通過修改前端 `Home.tsx` 組件，在 SQL 查詢成功後彈出 Modal，詢問用戶是否需要導出數據。

## 2. 環境準備

- 確保前端依賴 (`antd`) 已安裝（項目本身已有）。
- 確保開發服務器可運行：`npm run dev`。

## 3. 實施步驟

### 步驟 1: 狀態管理變更

**目標文件**: `frontend/src/pages/Home.tsx`

在 `Home` 組件內部增加一個新的狀態變量，用於控制導出提示彈窗的可見性。

```typescript
// [新增] 狀態定義
const [showExportPrompt, setShowExportPrompt] = useState(false);
```

### 步驟 2: 查詢邏輯增強

**目標文件**: `frontend/src/pages/Home.tsx`

修改 `handleExecuteQuery` 函數，在查詢成功且有數據返回時，設置彈窗狀態為 `true`。

```typescript
// [修改] handleExecuteQuery 函數
const handleExecuteQuery = async () => {
    // ... 前置檢查代碼 ...

    try {
        const response = await apiClient.post<QueryResult>(...);
        setQueryResult(response.data);
        message.success(...);

        // [新增] 自動提示邏輯
        if (response.data.rowCount > 0) {
            setShowExportPrompt(true);
        }
    } catch (error: any) {
        // ... 錯誤處理 ...
    } finally {
        setExecuting(false);
    }
};
```

### 步驟 3: 導出函數優化

**目標文件**: `frontend/src/pages/Home.tsx`

修改現有的 `exportToCSV` 和 `exportToJSON` 函數（或其調用者），確保在導出動作完成後關閉彈窗。

```typescript
// [修改] exportToCSV
const exportToCSV = () => {
    // ... 現有導出邏輯 ...
    
    // [新增] 關閉彈窗
    setShowExportPrompt(false);
};

// [修改] exportToJSON 同理
```

### 步驟 4: UI 組件渲染

**目標文件**: `frontend/src/pages/Home.tsx`

在組件的 `return` JSX 結構中（建議在最後一個 `</div>` 之前），添加 `Modal` 組件。

```tsx
// [新增] Modal 組件
<Modal
    title="Query Executed Successfully"
    open={showExportPrompt}
    onCancel={() => setShowExportPrompt(false)}
    footer={[
        <Button key="cancel" onClick={() => setShowExportPrompt(false)}>
            Cancel
        </Button>,
        <Button key="csv" onClick={handleExportCSV}>
            Export CSV
        </Button>,
        <Button key="json" type="primary" onClick={handleExportJSON}>
            Export JSON
        </Button>,
    ]}
>
    <p>
        Returned <strong>{queryResult?.rowCount}</strong> rows in{" "}
        <strong>{queryResult?.executionTimeMs}</strong>ms.
    </p>
    <p>Do you want to export the results?</p>
</Modal>
```

## 4. 驗證計劃

### 手動測試用雷

1. **場景一：普通查詢**
   - 操作：執行 `SELECT 1`。
   - 預期：查詢成功，表格顯示數據，彈出提示窗口。
2. **場景二：無數據查詢**
   - 操作：執行 `SELECT * FROM table WHERE 1=0`。
   - 預期：查詢成功，表格無數據，**不**彈出提示窗口。
3. **場景三：導出 CSV**
   - 操作：在彈窗中點擊 "Export CSV"。
   - 預期：瀏覽器下載 `.csv` 文件，彈窗自動關閉。
4. **場景四：取消**
   - 操作：在彈窗中點擊 "Cancel" 或右上角關閉圖標。
   - 預期：彈窗關閉，不執行下載。

## 5. 回滾計劃

如果引入了嚴重 Bug（如頁面崩潰或無限彈窗），將回退 `Home.tsx` 到修改前的版本。

- **備份**: 修改前請備份 `Home.tsx` 文件內容。
- **Git**: 如果使用 Git，可執行 `git checkout frontend/src/pages/Home.tsx` 撤銷更改。
