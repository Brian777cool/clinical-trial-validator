# 臨床試驗收案驗證系統 — 除錯與功能補強技術報告

> **專案**：clinical-trial-validator（Brian777cool）
> **報告範圍**：`validator.py` 核心驗證邏輯除錯、原始資料核對機制補齊、`app.py` 批次驗證功能開發，以及專案整理為獨立作品集的紀錄

---

## 一、問題背景

本系統的核心設計是**原始資料核對**：不論填報資料來自人工填寫或 LLM 抽取，都以模擬 EMR 資料庫為核對基準，一旦與病歷不符即攔截，避免錯誤數據進入收案判斷。專案初期把這個機制稱為「防幻覺（Anti-Hallucination）」，因為設計上也要攔下 LLM 抽錯或自行補值的數據。

在實際除錯過程中，發現程式碼雖然「看起來」實作了這個機制，但因多處縮排錯誤、邏輯耦合、資料缺漏等問題，導致核對功能**部分或完全未生效**。以下依發現順序記錄問題與對應解法，並補充批次驗證功能的開發過程。第二節記錄的是當時版本的程式與訊息，2026/09 的改動見第七節。

---

## 二、問題與解決紀錄

### 問題 1：BIA 檢查為永不執行的死碼

**現象**：不論相位角（Phase Angle）輸入多少數值，當時的 BIA 檢查（原稱「肌少症防線」，此說法已於 2026/09 版移除，見第七節）從未被觸發。

**原因**：`check_bia_safety()` 的呼叫程式碼被誤植於 `return` 陳述式之後、且多縮排一層，造成整段邏輯成為永遠無法執行到的死碼（dead code）。

**解法**：將 BIA 檢查邏輯移至與 platelet_count 比對同一縮排層級，確保比對到病患後會確實執行。同時補上 `found_patient` 旗標（當時版本），若病患 ID 查無 EMR 紀錄則明確回報錯誤，而非靜默放行。

---

### 問題 2：`validator.py` 與 Streamlit UI 邏輯耦合

**現象**：核心驗證檔案 `validator.py` 中混雜了完整的 Streamlit 表單程式碼，導致只要 `import validator` 就必須先安裝 `streamlit`，且網頁介面顯示的是寫死的假資料，並未真正呼叫驗證邏輯。

**解法**：將 Streamlit UI 程式碼完整移出至 `app.py`，透過 `from validator import validate_trial` 呼叫核心邏輯，使 CLI 驗證與網頁驗證共用同一套邏輯。當時也嘗試刪除重複定義的 `check_bia_safety()`，但未刪乾淨，直到 2026/09 版才清除（見第七節）。

---

### 問題 3：血液生化指標、BIA 欄位、腫瘤尺寸未納入核對

**現象**：表單中「相位角」「ECW Ratio」「膽紅素」「白蛋白」「INR」「腫瘤三徑」等欄位，不論輸入任何數值，驗證結果皆不受影響。

**原因**：`validate_trial()` 僅對 `platelet_count` 實作了「填報值 vs EMR 紀錄」的比對邏輯，其餘欄位雖然 EMR 資料庫中已有紀錄，卻從未被拿來比對。腫瘤三徑當時在 EMR 資料庫中甚至沒有對應欄位。

**解法**：
1. 於 `mock_emr_db.csv` 新增 `Tumor_Length_cm`、`Tumor_Width_cm`、`Tumor_Height_cm` 三個欄位
2. 比照 `platelet_count` 的模式，為 Bilirubin、Albumin、INR、ECW_Ratio、Phase_Angle、腫瘤三徑補齊比對邏輯（當時統一使用誤差容許值 0.1）

---

### 問題 4：迴圈變數殘留導致多筆病患誤判為同一結果

**現象**：在測試批次驗證功能時，發現不同病患輸入完全一致（與 EMR 相符）的資料，卻全部被誤判為「血小板數值不符 EMR」，唯獨 EMR 資料庫中最後一筆病患（P-1003）能正常通過驗證並繼續往下執行 Child-Pugh 計分。

**排查過程**：
1. 先以單筆 CLI 呼叫 `validator.py` 搭配一筆刻意與 EMR 完全相符的測試資料，結果依然誤判 → 確認問題出在 `validate_trial()` 本身，與 Streamlit、pandas、批次上傳流程無關
2. 逐行核對 `mock_emr_db.csv` 內容與測試資料，數值完全一致，排除資料本身錯誤的可能
3. 檢視 `validator.py` 的 `for row in reader:` 迴圈縮排，發現比對邏輯（`tolerance = 0.1` 及後續所有 EMR 比對判斷）縮排比 `if row['patient_id'] == data['patient_id']:` **少了兩層**，實際上已跑到迴圈範圍之外

**根本原因**：Python 的 `for` 迴圈執行完畢後，迴圈變數 `row` 不會被清空，而是停留在最後一次迭代的值。由於比對邏輯被誤放在迴圈外，不論驗證哪一位病患，程式實際比對的都是 `mock_emr_db.csv` 中**最後一列**的資料（本例為 P-1003）。這正好解釋了為何除了剛好等於最後一筆的病患外，其餘病患全數被誤判。

**解法**：將整段比對邏輯重新縮排至 `if row['patient_id'] == data['patient_id']:` 判斷式之內，確保比對只在找到對應病患的當下執行，而非依賴迴圈結束後的殘留值。2026/09 版進一步把「找病患」獨立成 `_find_emr_record()` 函式，從結構上避免這類錯誤。

**驗證結果**：以 CLI 重新測試 P-1001（資料與 EMR 完全相符）→ 正確輸出 `is_eligible: true` 與完整計算結果。

---

### 問題 5：路徑與環境相關的執行錯誤

| 錯誤現象 | 原因 | 解法 |
|---|---|---|
| `No such file or directory` | 終端機工作目錄與 `validator.py` 位置不一致 | 先 `cd` 至 `scripts` 資料夾；2026/09 版改以 `validator.py` 所在位置讀取 EMR，不再受工作目錄影響 |
| `ModuleNotFoundError: No module named 'streamlit'` | `validator.py` 當時仍耦合 Streamlit 程式碼 | 解耦後問題消失 |
| `streamlit : 無法辨識...` | PowerShell 找不到 `streamlit` 指令路徑 | 改用 `python -m streamlit run app.py` |

---

### 問題 6：Child-Pugh 分級指標未全部納入核對

**現象**：Child-Pugh 計分需要五項指標（Bilirubin、Albumin、INR、Ascites、Encephalopathy），但腹水與肝性腦病變當時在 EMR 資料庫中沒有對應欄位，這兩項完全信任填報資料。

**考量與決策**：補齊成本低（字串相等比對），且能讓決定收案資格的 Child-Pugh 計分所需的每一項都經過核對，因此決定補齊，而非留作已知限制。

**解法**：於 `mock_emr_db.csv` 新增 `Ascites`、`Encephalopathy` 兩欄位，並在 `validator.py` 加上字串比對。當時的程式碼如下：

```python
if row['Ascites'] != data['ascites']:
    return False, f"Hallucination detected! Real ascites status for {data['patient_id']} does not match EMR."
if row['Encephalopathy'] != data['encephalopathy']:
    return False, f"Hallucination detected! Real encephalopathy status for {data['patient_id']} does not match EMR."
```

**驗證結果**：以 CLI 重新測試 P-1001（兩欄皆與 EMR 相符）→ 正確通過，未被新增邏輯誤攔。至此，Child-Pugh 五項指標皆納入核對。

---

## 三、功能補強：批次驗證（Batch Validation）

### 設計動機

原始 Streamlit 表單僅支援單筆手動輸入，適合概念驗證，但不適合一次處理多筆收案資料的場景。

### 實作方式

在 `app.py` 中新增批次驗證區塊，透過 `st.file_uploader()` 接收 CSV 檔案，以 `pandas` 讀取後逐行呼叫既有的 `validate_trial()`（核心驗證邏輯不需修改，只在外層包裹迴圈），並將結果彙整為表格顯示，支援結果 CSV 下載。批次上傳檔只需包含本次要處理的病患，不需涵蓋 EMR 中的全部病患。

### 驗證測試（2026/09 版結果）

準備 9 筆病患資料，涵蓋通過、原始資料不符、Child-Pugh 不符、相位角示範規則、腫瘤體積示範規則 5 類情境；其他情境（缺漏欄位、格式錯誤、查無病患等）由單元測試涵蓋。

| 病患 | 驗證結果 | 原因 |
|---|---|---|
| P-1001 | ✅ 通過 | 與 EMR 一致，且符合收案條件 |
| P-1002 | ❌ 未通過 | Child-Pugh 13 分（Class C）＋相位角 3.2 |
| P-1003 | ❌ 未通過 | Child-Pugh 8 分（Class B） |
| P-2001 | ✅ 通過 | 與 EMR 一致，且符合收案條件 |
| P-2002 | ❌ 未通過 | 原始資料不符：血小板 |
| P-2003 | ❌ 未通過 | 相位角 3.5 |
| P-2004 | ❌ 未通過 | Child-Pugh 14 分（Class C）＋相位角 3.8 |
| P-2005 | ❌ 未通過 | 腫瘤體積 263.89 cm³ |
| P-2006 | ❌ 未通過 | 原始資料不符：腫瘤長徑 |

九筆病患各自得到獨立且正確的結果，未再出現迴圈殘留導致的誤判。

---

## 四、專案整理：從課程作業到獨立作品集

原始 repository 為課程期末專案，包含課程評分框架與其他賽道的檔案。整理時將與本專案核心功能無關的檔案移至本機備份資料夾（不納入版本控制），把測試資料移到 `scripts/` 與 `validator.py` 同層，並把原本綁定課程格式的 `SKILL.md` 改寫為 LLM 串接的設計說明。

---

## 五、修復後驗證測試

| 測試案例 | 預期結果 | 實際結果 |
|---|---|---|
| `test_pass.json`（P-1001，與 EMR 一致） | 通過，Class A | ✅ 通過 |
| P-1001，腫瘤長徑改為 8.0 | 原始資料不符 | ✅ 正確攔截 |
| `test_bia.json`（P-1002） | 未符合收案條件，列出 Class C 與相位角 | ✅ 正確攔截 |
| 批次上傳 9 筆病患 | 各自獨立判定 | ✅ 全數符合上表 |
| `pytest`（格式、缺漏、NaN、查無病患、EMR 不存在、分級邊界、批次） | 全數通過 | ✅ 26 passed |

---

## 六、結論與後續建議

本專案經歷四個階段：修復核心驗證邏輯中的縮排錯誤與比對缺漏，使核對範圍從只有血小板擴展到所有欄位；開發批次驗證功能，並在測試中發現迴圈變數殘留這個根本性 bug；補齊 Child-Pugh 五項指標的核對；最後將專案整理為獨立作品集。

後續若時間允許，建議優先處理：
1. 加入檢驗日期與篩選期（例如 14 天內）的檢查
2. 納入更接近真實試驗的條件，例如 BCLC 分期、ECOG、RECIST 可測量病灶
3. 把批次驗證邏輯從 `app.py` 抽成獨立函式並加上測試，再以 GitHub Actions 自動執行 pytest

---

## 七、版本更新紀錄（2026/09）

本次修正參考了 AI 輔助的程式碼審查建議，每項改動皆經本人確認並以測試驗證。

**驗證邏輯**
- 驗證順序改為：格式檢查 → 原始資料核對 → 收案條件判定；資料不一致時列出所有不符欄位並停止，收案條件則列出所有未符合的項目
- Child-Pugh、相位角規則與腫瘤體積一律以 EMR 原始資料計算
- 修正 Child-Pugh 的 PT-INR 分界為標準的 1.7–2.3（2 分）/ > 2.3（3 分）；腹水新增 `moderate`；腹水與肝性腦病變只接受允許的分級，未知字串回報格式錯誤
- 數值欄位拒絕空白、NaN、無限大、零與負值；血小板須為正整數
- 比對容許誤差改依各欄位的報告精度設定，取代統一的 0.1
- EMR 資料庫改以 `validator.py` 所在資料夾為準；資料庫不存在時直接回報錯誤，移除原本寫死的 fallback
- 移除仍重複定義的 `check_bia_safety()`，以及以固定體重 70 kg 推算的「安全劑量」計算（屬虛構公式，不宜出現在收案驗證工具中）

**用語**
- 相位角與腫瘤尺寸規則標示為「示範規則」，不再宣稱診斷肌少症；腫瘤徑長超過 20 cm 改為提示人工確認
- 訊息改為 `Source data mismatch`（原始資料不符）與 `Not eligible`（未符合收案條件）；「肝腦病變」更正為「肝性腦病變」，INR 標示為 PT-INR，表單加上單位

**資料與測試**
- 原本的批次資料在新增腹水／肝性腦病變核對後沒有同步更新，使 P-1002、P-1003 被擋在核對步驟，測不到原本要測的規則；本版修正資料，並調整部分模擬數值使其更符合臨床常理（如 Child-Pugh C 的病人有腹水、ECW/TBW 落在合理範圍）
- `test_validator.py` 擴充為 26 項測試；`requirements.txt` 補上 `streamlit`；移除重複的範例檔，CLI 輸出改為 `validation_result.json`