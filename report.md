# 臨床試驗智慧驗證系統 — 除錯與修復技術報告

> **專案**：clinical-trial-validator（Brian777cool）
> **報告範圍**：本次針對 `validator.py` 核心驗證邏輯與 `app.py` 前端介面進行之除錯、修復與功能補強紀錄

---

## 一、問題背景

本系統的核心設計精神為「防止幻覺（Anti-Hallucination）」：不論輸入來源是人工填寫或 LLM 產生，系統都應以 EMR 資料庫中的真實病歷紀錄為信任基準，比對使用者輸入是否一致，一旦不符即攔截，避免錯誤或竄改數據流入臨床試驗收案判斷。

在實際除錯過程中，發現程式碼雖然「看起來」實作了這個機制，但因多處縮排錯誤、邏輯耦合、資料缺漏等問題，導致防幻覺功能**部分或完全未生效**。以下依發現順序記錄問題與對應解法。

---

## 二、問題與解決紀錄

### 問題 1：BIA 安全檢查為永不執行的死碼

**現象**：不論相位角（Phase Angle）輸入多少數值，肌少症防線從未被觸發攔截。

**原因**：`check_bia_safety()` 的呼叫程式碼被誤植於 `return` 陳述式之後、且多縮排一層，造成整段邏輯成為永遠無法執行到的死碼（dead code）。

**解法**：將 BIA 檢查邏輯移至與 platelet_count 比對同一縮排層級，確保比對到病患後會確實執行。同時補上 `found_patient` 旗標，若病患 ID 查無 EMR 紀錄則明確回報錯誤，而非靜默放行。

---

### 問題 2：`validator.py` 與 Streamlit UI 邏輯耦合

**現象**：核心驗證檔案 `validator.py` 中混雜了完整的 Streamlit 表單程式碼，導致：
- 只要 `import validator`，就必須先安裝 `streamlit`，即使只是要做 CLI 驗證或 pytest 測試
- 網頁介面顯示的是寫死的假資料（`sample_output`），並未真正呼叫驗證邏輯

**解法**：將 Streamlit UI 程式碼完整移出，改由 `app.py` 專責前端呈現，並透過 `from validator import validate_trial` 呼叫核心邏輯，確保：
- `python validator.py <file>.json` 可獨立於 CLI / 自動化測試執行
- `streamlit run app.py` 呈現真實驗證結果，而非佔位假資料

同時移除檔案中重複定義兩次的 `check_bia_safety()` 函式。

---

### 問題 3：BIA 相關欄位使用者輸入未被採用

**現象**：在 Streamlit 表單中，無論「相位角」欄位輸入 0、270 或任何數值，驗證結果皆不受影響、永遠通過。

**原因**：`validate_trial()` 內部直接讀取 EMR 資料庫中的 `Phase_Angle`、`ECW_Ratio` 進行 BIA 運算，完全未讀取或比對表單傳入的 `data['phase_angle']`、`data['ecw_ratio']`，使用者輸入形同虛設。

**解法**：比照血小板計數（platelet_count）已驗證有效的模式，補上「輸入值 vs EMR 記錄」的比對邏輯——若誤差超出容許範圍（0.1），判定為 Hallucination 並攔截；比對通過後才採用 EMR 真實值繼續進行 BIA 運算。

---

### 問題 4：腫瘤尺寸完全無防幻覺機制

**現象**：`mock_emr_db.csv` 原始欄位中並無腫瘤三徑（長、寬、高）紀錄，導致此項關鍵臨床數據只做「型別檢查」與「絕對值上限（20cm、體積 250cm³）」，未曾與任何真實病歷比對。

**解法**：
1. 於 `mock_emr_db.csv` 新增 `Tumor_Length_cm`、`Tumor_Width_cm`、`Tumor_Height_cm` 三欄位並填入各病患對照數據
2. 於 `validator.py` 補上對應比對邏輯，誤差超出 0.1cm 即判定為 Hallucination 並攔截

**驗證結果**：測試 P-1001，將表單腫瘤長度改為 8.0（EMR 記錄為 4.0）→ 系統正確攔截並顯示 `Hallucination detected! Real tumor length for P-1001 does not match EMR.`

---

### 問題 5：Child-Pugh 計分相關欄位（Bilirubin、Albumin、INR）無防幻覺比對

**現象**：EMR 資料庫中雖收錄膽紅素、白蛋白、INR 數值，但 `validate_trial()` 從未拿來比對，直接採信表單輸入值進行 Child-Pugh 計分——而 Child-Pugh 分級正是決定收案資格（僅接受 Class A）的關鍵判斷依據，此缺口等同讓收案資格判斷完全繞過防幻覺機制。

**解法**：補上 Bilirubin、Albumin、INR 三項與 EMR 記錄的比對邏輯，與腫瘤尺寸、BIA 欄位採用相同的容許誤差模式（0.1）。

**已知限制**：腹水狀況（Ascites）、肝腦病變（Encephalopathy）因 EMR 資料庫原始設計並未收錄此二欄位，目前仍僅信任使用者輸入，無法進行防幻覺比對，於報告與 README 中已明確標註此範疇界線。

---

### 問題 6：路徑與環境相關的執行錯誤（除錯過程）

過程中亦排除數起與程式邏輯無關、但影響驗證流程的環境問題：

| 錯誤現象 | 原因 | 解法 |
|---|---|---|
| `No such file or directory` | 終端機工作目錄與 `validator.py` 實際位置不一致 | `cd` 至正確的 `scripts` 資料夾後再執行 |
| `ModuleNotFoundError: No module named 'streamlit'` | `validator.py` 當時仍耦合 Streamlit 程式碼（見問題 2） | 解耦後問題自然消失 |
| `streamlit : 無法辨識...` | PowerShell 找不到 `streamlit` 指令路徑 | 改用 `python -m streamlit run app.py` 執行 |
| `KeyError: 'Tumor_Length_cm'` | Streamlit 讀取到的 CSV 仍是舊版本（未包含新增欄位） | 重新確認 CSV 存檔狀態，並以 `Get-Content -TotalCount 1` 驗證標題列內容 |

---

## 三、修復後驗證測試

| 測試案例 | 預期結果 | 實際結果 |
|---|---|---|
| P-1001，所有欄位皆與 EMR 一致 | 驗證通過 | ✅ 通過 |
| P-1001，相位角改為 270（異常值） | 應攔截或至少不應無條件通過 | 已知限制：僅下限防呆，未設上限（見 README） |
| P-1001，腫瘤長度改為 8.0（與 EMR 4.0 不符） | 攔截並顯示 Hallucination 訊息 | ✅ 正確攔截 |
| test_bia.json（低相位角案例） | BIA 安全防線攔截 | ✅ 正確攔截，顯示肌少症警告 |

---

## 四、結論與後續建議

本次修復聚焦於讓「防幻覺」這個系統核心設計理念，從原本只在部分欄位（血小板計數）生效，擴展到血液生化指標、BIA 身體組成、腫瘤尺寸等多數關鍵臨床參數，使系統的實際行為與其命名精神一致。

後續若時間允許，建議優先處理：
1. 補上 EMR 未收錄之腹水、肝腦病變欄位，使 Child-Pugh 五項指標防幻覺覆蓋率達到 100%
2. 針對 BIA 相關生理數值（如相位角）增設合理性上限防呆，避免異常大值被誤判為合規輸入