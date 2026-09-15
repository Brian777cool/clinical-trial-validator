# 臨床試驗智慧驗證系統（Clinical Trial Validation System）

整合電子病歷（EMR）、身體組成分析（BIA）與腫瘤幾何尺寸的智慧化臨床試驗收案自動化驗證平台。本系統透過嚴格的多維度安全檢核與防幻覺（Anti-Hallucination）比對機制，確保受試者篩選流程的安全性與數據合規性，並支援單筆與批次兩種驗證模式，自動輸出標準的 Gold JSON / CSV 驗證結果。

> 本專案原為課程期末專案，現整理為獨立作品集項目。

---

## 系統架構

```
clinical-trial-validator/
│
├── skills/
│   └── open-trial-validator-Brian777cool/
│       └── scripts/
│           ├── app.py                  # Streamlit 互動式前端介面（單筆表單 + 批次上傳）
│           ├── validator.py            # 核心驗證邏輯與防呆引擎（EMR 比對、BIA、Child-Pugh、尺寸防呆）
│           ├── mock_emr_db.csv         # 模擬電子病歷資料庫（病患真實紀錄，比對基準）
│           ├── batch_input_test.csv    # 批次驗證測試用申請資料範例
│           └── output_gold.json        # 單筆驗證產出之標準 Gold JSON 結果
│
├── README.md
├── report.md                           # 除錯與功能開發技術報告
└── requirements.txt
```

`app.py` 與 `validator.py` 明確分工：前者僅負責 Streamlit UI 呈現與使用者輸入收集，後者為純邏輯運算核心，可獨立以 CLI 或 pytest 呼叫，不依賴 Streamlit 執行環境。

---

## 資料設計：EMR 資料庫 vs. 申請輸入資料

系統刻意將資料來源拆分為兩份角色不同的檔案，這是防幻覺機制成立的基礎：

| 檔案 | 角色 | 說明 |
|---|---|---|
| `mock_emr_db.csv` | 病患真實病歷（信任基準） | 代表醫院既有、經核實的官方紀錄，是所有病患的母體資料庫 |
| 使用者輸入 / 批次上傳檔 | 本次收案申請資料 | 代表這次填寫或由 LLM 生成的申請數據，需與 EMR 比對驗證真偽 |

兩者刻意分離的價值：
1. **防幻覺比對的前提**：若輸入與比對基準合併為同一份，系統將無從偵測資料是否被竄改或誤植
2. **彈性處理子集合**：批次輸入檔不需要涵蓋 EMR 資料庫中的所有病患，僅需包含「本次實際要處理的申請案」，貼近真實醫院場景中分批審核的作業模式

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
| 腹水狀況 (Ascites) | ✅ |
| 肝腦病變 (Encephalopathy) | ✅ |
| 細胞外液比率 (ECW Ratio) | ✅ |
| 相位角 (Phase Angle) | ✅ |
| 腫瘤長 / 寬 / 高 (Tumor Length/Width/Height) | ✅ |

**Child-Pugh 分級所需的五項指標（Bilirubin、Albumin、INR、Ascites、Encephalopathy）已達 100% 防幻覺覆蓋率**，收案資格判斷的每一項輸入都經過 EMR 真實紀錄核實，無死角。

比對邏輯採「逐筆病患獨立比對」設計：僅在於 EMR 中找到對應 `patient_id` 的該筆紀錄內執行比對，避免迴圈變數殘留造成誤判。若查無病患 ID 於 EMR 資料庫，系統會明確回報錯誤，不會靜默放行。

### 2. 解剖學防呆攔截

內建腫瘤三徑尺寸極限過濾（單一維度超過 20 cm 時自動攔截），杜絕異常輸入導致的數據失真。

### 3. BIA 身體組成安全檢核

- **肌少症防線**：相位角（Phase Angle）低於 4.0 時，直接判定無法承受標靶奈米載體代謝負荷，攔截收案。
- **腹水校正**：依細胞外液比率（ECW Ratio）自動校正乾重（Dry Weight），據以計算安全劑量。

### 4. 生理指標自動計算

- 即時計算腫瘤三維幾何體積（採用臨床標準三徑橢球公式：π/6 × 長 × 寬 × 高），並設有 250 cm³ 上限管制。
- 自動計算肝硬化嚴重度之 Child-Pugh 積分與分級（Class A / B / C），僅接受 Class A 收案。

### 5. 互動式網頁介面（單筆驗證）

提供直覺的 Streamlit 操作介面，病患下拉選單動態讀取 EMR 資料庫（新增病例僅需維護 `mock_emr_db.csv` 一份檔案，無需修改 `app.py`），驗證通過後支援一鍵下載標準化之 `output_gold.json`。

### 6. 批次驗證（CSV 上傳）

支援一次上傳包含多筆病患申請資料的 CSV，系統逐筆呼叫核心驗證邏輯並產出彙整結果表，無需一個一個透過表單手動輸入：

- 每筆申請資料依 `patient_id` 至 EMR 資料庫中獨立比對，結果互不干擾
- 彙整表清楚標示每筆申請的通過 / 未通過狀態與具體攔截原因
- 支援一鍵下載完整批次驗證結果 CSV

---

## 已知限制（Known Limitations）

- **BIA 數值上限**：相位角等生理指標目前僅設有下限防呆（如肌少症門檻），未設定生理合理性上限，極端異常大值（如打字誤植）可能未被攔截。此為刻意保留的已知限制，補齊需先制定合理的生理數值上限範圍，屬於後續可擴充項目。

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

新增病例需分兩步驟維護，缺一不可：

**1. 於 `mock_emr_db.csv` 建立該病患的真實病歷紀錄**（作為未來所有申請的比對基準）：

```
patient_id,platelet_count,Bilirubin,Albumin,INR,ECW_Ratio,Phase_Angle,Tumor_Length_cm,Tumor_Width_cm,Tumor_Height_cm,Ascites,Encephalopathy
```

**2. 於單筆表單輸入或 `batch_input_test.csv` 新增該病患的申請資料**（若欲測試正常通過案例，數值應與 EMR 紀錄一致）：

```
patient_id,platelet_count,bilirubin,albumin,inr,ecw_ratio,phase_angle,tumor_length_cm,tumor_width_cm,tumor_height_cm,ascites,encephalopathy
```

儲存 `mock_emr_db.csv` 後重新整理 Streamlit 頁面，新病例即會自動出現於單筆表單的病患 ID 下拉選單中，無需修改 `app.py`。

---

## 開發者資訊

- **開發者**：李羿昌 / **GitHub**：Brian777cool
- **核心模組**：`skills/open-trial-validator-Brian777cool`