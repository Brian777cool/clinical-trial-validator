# 臨床試驗智慧驗證系統 — 除錯與功能補強技術報告

> **專案**：clinical-trial-validator（Brian777cool）
> **報告範圍**：`validator.py` 核心驗證邏輯除錯、防幻覺機制補齊、`app.py` 批次驗證功能開發，以及專案整理為獨立作品集之完整紀錄

---

## 一、問題背景

本系統的核心設計精神為「防止幻覺（Anti-Hallucination）」：不論輸入來源是人工填寫或 LLM 產生，系統都應以 EMR 資料庫中的真實病歷紀錄為信任基準，比對使用者輸入是否一致，一旦不符即攔截，避免錯誤或竄改數據流入臨床試驗收案判斷。

在實際除錯過程中，發現程式碼雖然「看起來」實作了這個機制，但因多處縮排錯誤、邏輯耦合、資料缺漏等問題，導致防幻覺功能**部分或完全未生效**。以下依發現順序記錄問題與對應解法，並補充後續新增的批次驗證功能開發過程與防幻覺覆蓋率補齊工作。

---

## 二、問題與解決紀錄

### 問題 1：BIA 安全檢查為永不執行的死碼

**現象**：不論相位角（Phase Angle）輸入多少數值，肌少症防線從未被觸發攔截。

**原因**：`check_bia_safety()` 的呼叫程式碼被誤植於 `return` 陳述式之後、且多縮排一層，造成整段邏輯成為永遠無法執行到的死碼（dead code）。

**解法**：將 BIA 檢查邏輯移至與 platelet_count 比對同一縮排層級，確保比對到病患後會確實執行。同時補上 `found_patient` 旗標，若病患 ID 查無 EMR 紀錄則明確回報錯誤，而非靜默放行。

---

### 問題 2：`validator.py` 與 Streamlit UI 邏輯耦合

**現象**：核心驗證檔案 `validator.py` 中混雜了完整的 Streamlit 表單程式碼，導致只要 `import validator` 就必須先安裝 `streamlit`，且網頁介面顯示的是寫死的假資料，並未真正呼叫驗證邏輯。

**解法**：將 Streamlit UI 程式碼完整移出至 `app.py`，透過 `from validator import validate_trial` 呼叫核心邏輯，使 CLI 驗證與網頁驗證共用同一套真實邏輯。同時移除檔案中重複定義兩次的 `check_bia_safety()` 函式。

---

### 問題 3：BIA 相關欄位、血液生化指標、腫瘤尺寸缺乏防幻覺比對

**現象**：表單中「相位角」「ECW Ratio」「膽紅素」「白蛋白」「INR」「腫瘤三徑」等欄位，不論輸入任何數值，驗證結果皆不受影響。

**原因**：`validate_trial()` 僅對 `platelet_count` 實作了「輸入值 vs EMR 記錄」的比對邏輯，其餘欄位雖然 EMR 資料庫中已有記錄，卻從未被拿來比對，形同虛設。而腫瘤三徑當時 EMR 資料庫中甚至根本沒有對應欄位。

**解法**：
1. 於 `mock_emr_db.csv` 新增 `Tumor_Length_cm`、`Tumor_Width_cm`、`Tumor_Height_cm` 三個欄位
2. 比照 `platelet_count` 已驗證有效的模式，為 Bilirubin、Albumin、INR、ECW_Ratio、Phase_Angle、腫瘤三徑補齊比對邏輯（誤差容許值 0.1，避免浮點數精度誤判）

---

### 問題 4：迴圈變數殘留導致多筆病患誤判為同一結果

**現象**：在測試批次驗證功能時，發現不同病患輸入完全一致（與 EMR 相符）的資料，卻全部被誤判為「血小板數值不符 EMR」，唯獨 EMR 資料庫中最後一筆病患（P-1003）能正常通過驗證並繼續往下執行 Child-Pugh 計分。

**排查過程**：
1. 先以單筆 CLI 呼叫 `validator.py` 搭配一筆刻意與 EMR 完全相符的測試資料，結果依然誤判 → 確認問題出在 `validate_trial()` 本身，與 Streamlit、pandas、批次上傳流程無關
2. 逐行核對 `mock_emr_db.csv` 內容與測試資料，數值完全一致，排除資料本身錯誤的可能
3. 檢視 `validator.py` 的 `for row in reader:` 迴圈縮排，發現比對邏輯（`tolerance = 0.1` 及後續所有 EMR 比對判斷）縮排比 `if row['patient_id'] == data['patient_id']:` **少了兩層**，實際上已跑到迴圈範圍之外

**根本原因**：Python 的 `for` 迴圈執行完畢後，迴圈變數 `row` 不會被清空，而是停留在最後一次迭代的值。由於比對邏輯被誤放在迴圈外，不論驗證哪一位病患，程式實際比對的都是 `mock_emr_db.csv` 中**最後一列**的資料（本例為 P-1003）。這正好解釋了為何除了剛好等於最後一筆的病患外，其餘病患全數被誤判。

**解法**：將 `tolerance = 0.1` 起至 `data['calibrated_safe_dose_mg'] = bia_result` 止的整段比對邏輯，重新縮排至 `if row['patient_id'] == data['patient_id']:` 判斷式之內，確保比對邏輯僅在找到對應病患的當下執行，而非依賴迴圈結束後的殘留值。

**驗證結果**：以 CLI 重新測試 P-1001（資料與 EMR 完全相符）→ 正確輸出 `is_eligible: true`，包含完整計算結果（安全劑量、腫瘤體積、Child-Pugh 分級）。

---

### 問題 5：路徑與環境相關的執行錯誤（除錯過程共通問題）

過程中反覆排除與程式邏輯無關、但影響驗證流程的環境問題：

| 錯誤現象 | 原因 | 解法 |
|---|---|---|
| `No such file or directory` / `File does not exist` | 終端機工作目錄與 `validator.py` 實際位置不一致 | `cd` 至正確的 `scripts` 資料夾後再執行 |
| `ModuleNotFoundError: No module named 'streamlit'` | `validator.py` 當時仍耦合 Streamlit 程式碼 | 解耦後問題自然消失 |
| `streamlit : 無法辨識...` | PowerShell 找不到 `streamlit` 指令路徑 | 改用 `python -m streamlit run app.py` 執行 |
| `KeyError: 'Tumor_Length_cm'` | Streamlit 讀取到尚未儲存最新內容的 CSV 版本 | 以 `Get-Content -TotalCount 1` 直接驗證磁碟上檔案的實際標題列 |

---

### 問題 6：Child-Pugh 分級指標防幻覺覆蓋率未達 100%

**現象**：Child-Pugh 分級計算需要五項指標（Bilirubin、Albumin、INR、Ascites、Encephalopathy），但腹水狀況（Ascites）與肝腦病變（Encephalopathy）當時在 EMR 資料庫中並未收錄對應欄位，這兩項指標完全信任使用者輸入，無防幻覺比對能力。

**考量與決策**：評估後認為此缺口的補齊成本低（字串相等比對，不需誤差容許值），且能讓決定收案資格的核心演算法（Child-Pugh 分級）達到完整的防幻覺覆蓋，因此決定補齊，而非留作已知限制。

**解法**：
1. 於 `mock_emr_db.csv` 新增 `Ascites`、`Encephalopathy` 兩欄位
2. 於 `validator.py` 中，緊接在 INR 比對邏輯之後，補上：
```python
if row['Ascites'] != data['ascites']:
    return False, f"Hallucination detected! Real ascites status for {data['patient_id']} does not match EMR."
if row['Encephalopathy'] != data['encephalopathy']:
    return False, f"Hallucination detected! Real encephalopathy status for {data['patient_id']} does not match EMR."
```

**驗證結果**：以 CLI 重新測試 P-1001（`ascites`、`encephalopathy` 皆與 EMR 相符）→ 正確通過驗證，未被新增邏輯誤攔。至此，Child-Pugh 分級所需的五項指標已達 100% 防幻覺覆蓋率。

---

## 三、功能補強：批次驗證（Batch Validation）

### 設計動機

原始 Streamlit 表單僅支援單筆病患手動輸入，適合概念驗證與 demo，但不適合實務上需要一次處理多筆收案申請的場景。

### 實作方式

在 `app.py` 中新增批次驗證區塊，透過 `st.file_uploader()` 接收 CSV 檔案，以 `pandas` 讀取後逐行呼叫既有的 `validate_trial()`（**核心驗證邏輯未經任何修改**，僅是外層包裹迴圈），並將結果彙整為表格顯示，支援結果 CSV 下載。

### 資料架構設計原則

批次功能沿用系統既有的雙資料來源設計：

- `mock_emr_db.csv`：病患真實病歷資料庫，作為比對基準
- 批次上傳檔：本次待驗證的申請資料子集合，僅需包含實際要處理的病患，不需涵蓋 EMR 資料庫全部病患

此設計貼近真實醫院場景中分批審核申請案的作業模式，同時維持防幻覺比對機制的完整性。

### 驗證測試

準備 9 筆病患資料，涵蓋系統內全部攔截機制，驗證批次功能是否能對每一筆病患給出獨立、正確的判定結果：

| 病患 | 驗證結果 | 觸發機制 |
|---|---|---|
| P-1001 | ✅ 通過 | 全部欄位與 EMR 相符 |
| P-1002 | ❌ 未通過 | BIA 肌少症防線（相位角 3.2） |
| P-1003 | ❌ 未通過 | Child-Pugh Class B，不符收案條件 |
| P-2001 | ✅ 通過 | 全部欄位與 EMR 相符 |
| P-2002 | ❌ 未通過 | 血小板幻覺（輸入與 EMR 不符） |
| P-2003 | ❌ 未通過 | BIA 肌少症防線（相位角 3.5） |
| P-2004 | ❌ 未通過 | Child-Pugh Class C |
| P-2005 | ❌ 未通過 | 腫瘤體積超過 250 cm³ 上限 |
| P-2006 | ❌ 未通過 | 腫瘤長度幻覺（輸入與 EMR 不符） |

結果顯示，修正問題 4 後，九筆病患皆各自得到正確且獨立的驗證結果，涵蓋系統內全部六種攔截機制，未再出現迴圈殘留導致的誤判。

---

## 四、專案整理：從課程作業到獨立作品集

原始 repository 作為課程期末專案，包含大量課程評分基礎設施（`run_dev.py` 自動評分驅動程式、`tests/` 目錄下配合評分邏輯的測試檔案、`dev_set/` 課程範例資料、`.github/workflows/classroom.yml` GitHub Classroom CI/CD、`PAIRWISE_ROLE.md` 及 `good_code.json` / `bad_code.json` 等 Pairwise 賽道專屬檔案，本專案實際採用 Open Track，與 Pairwise 賽道機制無關）。

為將本專案整理為可對外展示的獨立作品集，進行以下處理：

1. **清理課程框架殘留檔案**：確認 `OPEN_TRACK.md` 內容後，判定上述檔案均與本專案核心功能無關，予以移除或隔離。為保留本機備份以防萬一，將檔案集中移至 `_pairwise_track_unused/` 目錄，並於 `.gitignore` 中加入排除規則，確保不納入版本控制。
2. **統一測試資料位置**：將原先散落於專案根目錄的測試檔案（`test_bia.json`、`test_pass.json` 等）移入 `scripts/` 目錄，與 `validator.py` 同層級，避免執行時的路徑混淆問題。
3. **重寫 `SKILL.md`**：原檔案格式綁定課程專屬的 Hermes Agent metadata 與 slash command 呼叫方式，與作品集用途不符。改寫為通用的「LLM Integration Guide」，聚焦說明「確定性軟體外殼包覆機率性模型」的架構設計理念，移除課程框架專屬語法。

---

## 五、修復後完整驗證測試

| 測試案例 | 預期結果 | 實際結果 |
|---|---|---|
| P-1001，所有欄位皆與 EMR 一致（CLI 單筆） | 驗證通過 | ✅ 通過 |
| P-1001，腫瘤長度改為 8.0（與 EMR 不符） | 攔截並顯示 Hallucination 訊息 | ✅ 正確攔截 |
| test_bia.json（低相位角案例） | BIA 安全防線攔截 | ✅ 正確攔截，顯示肌少症警告 |
| 批次上傳 9 筆病患，涵蓋 6 種攔截情境 | 各自獨立判定 | ✅ 全數正確 |
| P-1001，ascites / encephalopathy 與 EMR 一致 | 驗證通過，不受新增邏輯誤攔 | ✅ 通過 |

---

## 六、結論與後續建議

本次工作可分為四個階段：第一階段修復核心驗證邏輯中多處縮排錯誤與比對缺漏，使「防幻覺」機制的覆蓋範圍從原本僅有血小板一項欄位，擴展至血液生化指標、BIA 身體組成、腫瘤尺寸等多數關鍵臨床參數；第二階段開發批次驗證功能，並在測試過程中意外發現迴圈變數殘留這一根本性 bug；第三階段補齊 Child-Pugh 分級所需五項指標的防幻覺覆蓋，使收案資格判斷不再有防幻覺死角；第四階段將專案自課程作業整理為聚焦核心功能的獨立作品集。

後續若時間允許，建議優先處理：
1. 針對 BIA 相關生理數值（如相位角）增設合理性上限防呆，避免異常大值被誤判為合規輸入——此為目前唯一保留的已知限制
2. 為批次驗證功能補上單元測試，特別針對「多筆病患、部分符合部分不符合 EMR」的混合情境，避免問題 4 這類迴圈邏輯錯誤再次發生而未被察覺