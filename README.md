# 臨床試驗收案驗證系統（Clinical Trial Eligibility Validator）

以規則式邏輯實作的臨床試驗收案驗證工具，以「肝癌標靶奈米藥物試驗」作為假想情境。系統把研究端填報的收案資料與模擬的電子病歷（EMR）逐項核對，一致後再以 EMR 原始資料計算 Child-Pugh 分級，並判斷是否符合收案條件；支援單筆與批次兩種驗證模式，輸出 JSON / CSV 驗證結果。

> 本專案原為課程期末專案，現整理為獨立作品集項目。

> ⚠️ **聲明**：本專案所有病患資料皆為模擬資料，不含任何真實病歷。BIA 相位角、腫瘤尺寸與體積的閾值為自訂的示範規則，並非真實臨床試驗的收案標準；假想試驗的條件也刻意不完整（未含 BCLC 分期、ECOG、病毒學、先前治療等）。本系統僅供學習與展示，不可用於臨床決策。

---

## 系統架構

```
clinical-trial-validator/
│
├── skills/
│   └── open-trial-validator-Brian777cool/
│       ├── SKILL.md                    # LLM 串接的設計構想（本 repo 未實作 LLM 串接）
│       └── scripts/
│           ├── app.py                  # Streamlit 互動式前端介面（單筆表單 + 批次上傳）
│           ├── validator.py            # 核心驗證邏輯（原始資料核對、Child-Pugh、示範規則）
│           ├── test_validator.py       # pytest 單元測試
│           ├── mock_emr_db.csv         # 模擬電子病歷資料庫（核對基準）
│           ├── batch_input_test.csv    # 批次驗證範例資料
│           ├── test_pass.json          # CLI 範例輸入（符合收案條件）
│           ├── test_bia.json           # CLI 範例輸入（未符合收案條件）
│           └── sample_output.json      # CLI 輸出範例
│
├── README.md
├── report.md                           # 除錯與功能開發技術報告
└── requirements.txt
```

`app.py` 只負責 Streamlit 介面與輸入收集，`validator.py` 為純邏輯核心，可獨立以 CLI 或 pytest 呼叫，不依賴 Streamlit。

---

## 資料設計：EMR 原始資料 vs. 填報資料

| 檔案 | 角色 | 說明 |
|---|---|---|
| `mock_emr_db.csv` | 模擬 EMR（核對基準） | 模擬醫院既有的病歷紀錄 |
| 單筆表單 / 批次上傳檔 | 研究端填報的收案資料 | 可能由人工填寫，或未來由 LLM 從病歷文字抽取，都必須先與 EMR 核對 |

兩者刻意分開，系統才能偵測填報資料是否誤植或與病歷不符。這個概念上對應臨床試驗中的原始資料核對（source data verification, SDV），但本系統只是自動化的欄位比對，並不等同監測員執行的完整 SDV。

---

## 驗證流程

`validate_trial()` 依序執行：

1. **欄位完整性與格式檢查**：缺漏或空白欄位、非數值、NaN、零或負值、未知的腹水／肝性腦病變分級，一律拒絕
2. **資料合理性檢查**：腫瘤單一徑長超過 20 cm 時拒絕，並提示人工確認數值（示範上限）
3. **原始資料核對**：與 `mock_emr_db.csv` 中對應病患的紀錄逐項比對，列出所有不一致的欄位並停止，請使用者核對原始文件；EMR 資料庫不存在或查無病患時一律拒絕，不會靜默放行
4. **收案條件判定**：以 EMR 原始資料計算，列出**所有**未符合的條件
   - Child-Pugh 僅收 Class A
   - 相位角 < 4.0°（示範規則）
   - 腫瘤體積 > 250 cm³（示範規則，以三徑橢球公式估算）

### 原始資料核對欄位

| 欄位 | 單位 | 比對方式 |
|---|---|---|
| 血小板 (Platelet) | /µL | 正整數，須完全相符 |
| 總膽紅素 (Bilirubin) | mg/dL | 誤差 ≤ 0.05 |
| 白蛋白 (Albumin) | g/dL | 誤差 ≤ 0.05 |
| PT-INR | — | 誤差 ≤ 0.005 |
| ECW/TBW 比值 | — | 誤差 ≤ 0.005 |
| 相位角 (Phase Angle, 50 kHz) | ° | 誤差 ≤ 0.05 |
| 腫瘤長徑 / 寬徑 / 頭尾徑 | cm | 誤差 ≤ 0.05 |
| 腹水 (Ascites) | — | 須完全相符 |
| 肝性腦病變 (Hepatic Encephalopathy) | — | 須完全相符 |

差距不超過各欄位報告最小單位的一半，即視為一致（本模擬資料的 ECW/TBW 以兩位小數記錄；實際儀器多報到小數點後三位）。血小板目前只做核對，未作為收案條件。

### Child-Pugh 計分標準

| 指標 | 1 分 | 2 分 | 3 分 |
|---|---|---|---|
| Bilirubin (mg/dL) | < 2.0 | 2.0–3.0 | > 3.0 |
| Albumin (g/dL) | > 3.5 | 2.8–3.5 | < 2.8 |
| PT-INR | < 1.7 | 1.7–2.3 | > 2.3 |
| Ascites | none | mild | moderate / severe |
| Hepatic encephalopathy (West Haven) | none | grade 1–2 | grade 3–4 |

總分 5–6 分為 Class A、7–9 分為 Class B、10–15 分為 Class C。本系統以 EMR 原始資料計分，避免比對容許誤差讓分級在邊界翻轉。

### BIA 身體組成（示範規則）

相位角常被用來反映細胞膜完整性與營養狀態，但它本身並不是肌少症或收案資格的診斷標準；而且在有腹水或水腫的病人，BIA 的推估本來就不可靠。本系統以「相位角 < 4.0°」作為自訂的示範規則，只是用來展示如何把身體組成指標納入檢核。ECW/TBW 比值目前只做核對，不參與判斷。

---

## 互動式網頁介面

- **單筆驗證**：病患下拉選單直接讀取 EMR 資料庫，驗證通過後可下載 `validation_result.json`。
- **批次驗證**：上傳多筆填報資料的 CSV，系統逐筆核對並產出彙整表，可下載結果 CSV。CSV 一律以文字讀入，空白欄位會被判定為缺漏。

---

## 已知限制（Known Limitations）

- **全部為模擬資料**：未以真實病歷驗證；若要使用真實資料，須先通過人體研究倫理審查（IRB）並完成去識別化。
- **示範閾值**：相位角 4.0°、腫瘤徑長 20 cm、腫瘤體積 250 cm³ 皆為自訂的示範規則，非臨床標準。真實的肝癌試驗通常以 RECIST 1.1 / mRECIST 的可測量病灶與 BCLC 分期來定義腫瘤負荷。
- **未涵蓋的臨床細節**：未處理檢驗日期與篩選期、抗凝血劑對 INR 的影響、輸注白蛋白後的數值、以藥物控制的腹水或肝性腦病變等情況。
- **EMR 資料品質**：系統以 EMR 為核對基準，若 EMR 本身有誤，核對結果也會跟著錯。
- **LLM 串接**：`SKILL.md` 描述的是讓 LLM 從病歷文字抽取數值、再交給本系統核對的設計構想，本 repo 目前未實作 LLM 串接。

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

**以 CLI 方式執行單筆驗證：**

```bash
cd skills/open-trial-validator-Brian777cool/scripts
python validator.py test_pass.json
```

執行成功後會輸出 `validation_result.json`（已列入 `.gitignore`），格式同 `sample_output.json`。

**執行單元測試：**

```bash
cd skills/open-trial-validator-Brian777cool/scripts
python -m pytest -q
```

---

## 新增病例資料

**1. 於 `mock_emr_db.csv` 建立該病患的模擬 EMR 紀錄**：

```
patient_id,platelet_count,Bilirubin,Albumin,INR,ECW_Ratio,Phase_Angle,Tumor_Length_cm,Tumor_Width_cm,Tumor_Height_cm,Ascites,Encephalopathy
```

**2. 於單筆表單或批次 CSV 輸入該病患的填報資料**（若要測試通過案例，數值應與 EMR 一致）：

```
patient_id,platelet_count,bilirubin,albumin,inr,ecw_ratio,phase_angle,tumor_length_cm,tumor_width_cm,tumor_height_cm,ascites,encephalopathy
```

`ascites` 只接受 `none`、`mild`、`moderate`、`severe`；`encephalopathy` 只接受 `none`、`grade 1`～`grade 4`。

---

## 開發者資訊

- **開發者**：李羿昌 / **GitHub**：Brian777cool
- **核心模組**：`skills/open-trial-validator-Brian777cool`