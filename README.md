# 臨床試驗智慧驗證系統（Clinical Trial Validation System）

整合電子病歷（EMR）、身體組成分析（BIA）與腫瘤幾何尺寸的智慧化臨床試驗收案自動化驗證平台。本系統透過嚴格的多維度安全檢核與防幻覺（Anti-Hallucination）比對機制，確保受試者篩選流程的安全性與數據合規性，並自動輸出標準的 Gold JSON 驗證結果。

---

## 系統架構

```
open-trial-validator-Brian777cool/
│
├── scripts/
│   ├── app.py              # Streamlit 互動式前端介面
│   ├── validator.py        # 核心驗證邏輯與防呆引擎（EMR 比對、BIA、Child-Pugh、尺寸防呆）
│   ├── mock_emr_db.csv     # 模擬電子病歷資料庫
│   └── output_gold.json    # 產出之標準 Gold JSON 驗證結果
└── requirements.txt        # 專案相依套件清單
```

`app.py` 與 `validator.py` 已明確分工：前者僅負責 Streamlit UI 呈現與使用者輸入收集，後者為純邏輯運算核心，可獨立以 CLI 或 pytest 呼叫，不依賴 Streamlit 執行環境。

---

## 核心功能與防呆機制

### 1. EMR 防幻覺比對（Hallucination Detection）

系統以 `mock_emr_db.csv` 中的官方病歷紀錄為信任基準，將使用者（或 LLM）輸入的數值與真實紀錄逐一比對，任何不一致將立即攔截並拒絕驗證：

| 欄位 | 防幻覺比對 |
|---|---|
| 血小板計數 (Platelet Count) | ✅ |
| 膽紅素 (Bilirubin) | ✅ |
| 白蛋白 (Albumin) | ✅ |
| 凝血酶原時間比 (INR) | ✅ |
| 細胞外液比率 (ECW Ratio) | ✅ |
| 相位角 (Phase Angle) | ✅ |
| 腫瘤長 / 寬 / 高 (Tumor Length/Width/Height) | ✅ |
| 腹水狀況 (Ascites) | ⚠️ EMR 無此欄位，無法比對 |
| 肝腦病變 (Encephalopathy) | ⚠️ EMR 無此欄位，無法比對 |

若查無病患 ID 於 EMR 資料庫，系統會明確回報錯誤，不會靜默放行。

### 2. 解剖學防呆攔截

內建腫瘤三徑尺寸極限過濾（單一維度超過 20 cm 時自動攔截），杜絕異常輸入導致的數據失真。

### 3. BIA 身體組成安全檢核

- **肌少症防線**：相位角（Phase Angle）低於 4.0 時，直接判定無法承受標靶奈米載體代謝負荷，攔截收案。
- **腹水校正**：依細胞外液比率（ECW Ratio）自動校正乾重（Dry Weight），據以計算安全劑量。

### 4. 生理指標自動計算

- 即時計算腫瘤三維幾何體積（採用臨床標準三徑橢球公式：π/6 × 長 × 寬 × 高），並設有 250 cm³ 上限管制。
- 自動計算肝硬化嚴重度之 Child-Pugh 積分與分級（Class A / B / C），僅接受 Class A 收案。

### 5. 互動式網頁與標準輸出

提供直覺的 Streamlit 操作介面，病患下拉選單動態讀取 EMR 資料庫（新增病例僅需維護 `mock_emr_db.csv` 一份檔案），驗證通過後支援一鍵下載標準化之 `output_gold.json`。

---

## 已知限制（Known Limitations）

- **腹水狀況、肝腦病變**：因 EMR 資料庫未收錄此二項欄位，目前僅信任使用者輸入，無防幻覺比對能力。
- **BIA 數值上限**：相位角等生理指標目前僅設有下限防呆（如肌少症門檻），未設定生理合理性上限，極端異常大值（如打字誤植）可能未被攔截。

---

## 安裝與快速啟動步驟

**安裝必要套件：**

```bash
pip install -r requirements.txt
```

**啟動互動網頁介面：**

```bash
cd skills/open-trial-validator-Brian777cool/scripts
python -m streamlit run app.py
```

**以 CLI 方式執行單筆驗證（供自動化測試 / pytest 使用）：**

```bash
python validator.py <輸入資料.json>
```

執行成功後，會於當前目錄輸出 `output_gold.json` 作為標準驗證結果。

---

## 新增病例資料

於 `mock_emr_db.csv` 新增一列，依序填入：

```
patient_id,platelet_count,Bilirubin,Albumin,INR,ECW_Ratio,Phase_Angle,Tumor_Length_cm,Tumor_Width_cm,Tumor_Height_cm
```

儲存後重新整理 Streamlit 頁面，新病例即會自動出現於病患 ID 下拉選單中，無需修改 `app.py`。

---

## 學生資訊

- **學生**：李羿昌 / **GitHub**：Brian777cool
- **專案類別**：個人獨立完成組
- **核心模組**：`skills/open-trial-validator-Brian777cool`