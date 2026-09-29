# LLM Integration Guide: Clinical Trial Eligibility Validator

> **說明**：本文件描述「讓 LLM 從病歷文字抽取數值，再交給本系統核對與判定」的設計構想。本 repo 目前只實作驗證引擎（`validator.py`），尚未實作 LLM 串接與重試流程。抽取效果的初步評估見 repo 最外層的 `llm_eval/`。

## 設計理念：確定性運算包覆機率性模型

核心理念是「用確定性軟體外殼（Deterministic Harness）包覆機率性模型（Probabilistic LLM）」。在臨床試驗收案的情境中，數據的微小失真就可能影響受試者安全與試驗合規，因此把「自然語言特徵抽取」與「數值運算、判定」完全分開：

- **LLM 的角色**：只負責從病歷原文抽取結構化數值，不執行任何計算或判斷
- **`validator.py` 的角色**：接收結構化數值後，執行與 EMR 原始資料的核對、所有計算與收案資格判定，結果完全可重現

LLM 抽取的數值若與病歷不符（例如抽錯或自行補值，也就是俗稱的「幻覺」），會在原始資料核對這一步被攔下。

## 適用情境

以假想的「肝癌標靶奈米藥物試驗」為情境（所有病患資料皆為模擬資料，示範閾值非臨床標準），當病歷資料以非結構化文字（如醫師病歷記載、影像報告）形式提供時，示範 LLM 與驗證引擎如何分工。

## 操作流程

### 1. 從病歷原文抽取結構化數值，**不要自行計算分數或體積**

需抽取的欄位：

- `patient_id`（病患編號，如 P-1001）
- `platelet_count`（血小板，/µL，正整數；台灣檢驗報告常以 ×10³/µL 表示，例如 85 應換算為 85000）
- `bilirubin`（總膽紅素，mg/dL）
- `albumin`（白蛋白，g/dL）
- `inr`（PT-INR，凝血酶原時間國際標準化比值）
- `ecw_ratio`（ECW/TBW 比值，BIA 檢測數值）
- `phase_angle`（相位角，°，BIA 檢測數值）
- `tumor_length_cm`、`tumor_width_cm`、`tumor_height_cm`（腫瘤長徑、寬徑、頭尾徑，cm）
- `ascites`（腹水，僅限 "none", "mild", "moderate", "severe"）
- `encephalopathy`（肝性腦病變，West Haven 分級，僅限 "none", "grade 1", "grade 2", "grade 3", "grade 4"）

**抽取原則：**
- 只抽取病歷中明確記載的原始數值，不得推估、四捨五入或補值
- 若病歷中某必要欄位未記載，應明確標示「缺漏」，不得自行假設預設值
- 腫瘤三徑務必分別記錄三個獨立數值，不得只記錄單一「腫瘤大小」
- `ascites`、`encephalopathy` 務必依病歷原文對應到指定選項，不得自行意譯或合併分級（例如「輕微腹水」應對應 `"mild"`）；未知字串會被判定為格式錯誤

### 2. 呼叫驗證引擎，不要自行計算

所有核對、Child-Pugh 計分、腫瘤體積（三徑橢球體積估算公式）與收案判定，一律交由 `validator.py` 的 `validate_trial()` 執行。即使 LLM 自行推論出收案結論，也應以驗證引擎的結果為準。

### 3. 單筆評估

```bash
python validator.py <輸入資料.json>
```

### 4. 批次評估

將多筆資料整理為單一 CSV，透過 `app.py` 的批次上傳區塊上傳，系統逐筆核對並產出彙整表。

## 驗證引擎的把關邏輯

`validate_trial()` 依序執行：

1. **欄位完整性與格式檢查**：缺漏或空白欄位、非數值、NaN、零或負值、未知分級，直接拒絕
2. **資料合理性檢查**：腫瘤任一徑長超過 20 cm 時拒絕，並提示人工確認數值（示範上限）
3. **原始資料核對**：與 `mock_emr_db.csv` 中對應病患的紀錄逐項比對，列出所有不一致的欄位；EMR 資料庫不存在或查無病患時直接拒絕
4. **收案條件判定**（以 EMR 原始資料計算，列出所有未符合的條件）：Child-Pugh 僅收 Class A；相位角 < 4.0°、腫瘤體積 > 250 cm³ 為示範規則

## 回傳訊息類型

| 類型 | 意義 |
|---|---|
| `Missing required field` | 缺少必要欄位或欄位空白 |
| `Data Type Violation` | 數值格式錯誤、非正數，或分級不在允許選項內 |
| `Data Error` | 腫瘤徑長超過示範上限、EMR 資料庫不存在、查無病患，或 EMR 紀錄格式錯誤 |
| `Source data mismatch` | 填報資料與 EMR 原始資料不符，需核對原始文件 |
| `Not eligible` | 資料一致，但未符合收案條件 |

驗證通過時，輸出包含 `calculated_cp_score`、`calculated_cp_class`、`calculated_tumor_volume_cm3` 與 `is_eligible: true` 的 JSON。