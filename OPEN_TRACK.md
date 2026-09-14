## 1. Skill 簡介

本專案是一個「主動標靶 PLGA 奈米載體肝癌治療收案驗證器」，透過 Python 確定性腳本攔截 LLM 對病歷的處理，執行 EMR 防幻覺核對、Child-Pugh 演算法計分與腫瘤幾何體積驗證。

## 2. Skill 名稱與目錄

skills/open-trial-validator-Brian777cool/

## 3. 呼叫方式

**Slash command:**

```bash
/open-trial-validator-Brian777cool
```

**輸入 JSON 範例:**

```json
{
  "task_id": "open_hcc_001",
  "patient_record": "Patient ID: P-1001. A 55-year-old male presents with hepatocellular carcinoma. MRI reveals a solitary tumor measuring 12.5 cm in length and 5.0 cm in width. Recent lab results indicate platelet count of 85,000 /uL. Liver function tests show total bilirubin 1.2 mg/dL, albumin 3.8 g/dL, and an INR of 1.1. Ultrasound indicates no ascites. The patient is fully alert with no signs of encephalopathy."
}
```

**輸出 JSON 範例(此即輸出 schema):**

```json
{
  "patient_id": "P-1002",
  "platelet_count": 42000,
  "tumor_length_cm": 5.0,
  "tumor_width_cm": 5.0,
  "tumor_height_cm": 4.0,
  "calculated_tumor_volume_cm3": 52.36,
  "calibrated_safe_dose_mg": 4.25,
  "bilirubin": 1.5,
  "albumin": 3.0,
  "inr": 1.2,
  "ascites": "none",
  "encephalopathy": "none",
  "calculated_cp_score": 6,
  "calculated_cp_class": "B"
}
```

## 4. 自定 Verifiable Scenario

**Scenarios(請提供至少 3 個):**

- Scenario 1 (Perfect Match): 一位完全符合收案標準的肝癌初期病患 (P-1001)，各項檢驗數值與 EMR 資料庫一致，且腫瘤體積算出小於 250 cm^3，Child-Pugh 算出為 Class A。預期輸出 is_eligible: true。
- Scenario 2 (Hallucination Trap): 故意在病歷文字中給出錯誤的血小板數據 (如 100,000)，或刻意引導 LLM 捏造。預期 Python 腳本會核對 mock_emr_db.csv (P-1002 真實為 42,000) 並觸發 sys.exit(1) 報錯，擋下幻覺。
- Scenario 3 (Algorithmic Rejection): 給出一名腫瘤過大 (L=22, W=10) 且肝功能不佳的病患。預期 LLM 雖正確抽取數據，但 Python 會計算出腫瘤體積超標 (1100 cm^3) 與 Child-Pugh Score 達 C 級，觸發 Medical Rule Violation 並中斷流程。

**Metric:**
評分器藉由比對最終輸出的 JSON 是否存在。對於 Scenario 1，必須輸出如 Schema 所列之完整 JSON (包含精確的數學計算欄位)；對於 Scenario 2 與 3，預期驗證腳本會持續報錯導致重試次數耗盡，最終無法產出合格的 is_eligible: true JSON。

**為何不可 gameable:**
1. LLM 無法事先得知 mock_emr_db.csv 內的真實血小板數據，必須透過腳本核對，無法靠硬核 (hardcode) 答案通過幻覺測試。
2. calculated_tumor_volume_cm3 與 calculated_cp_class 的結果由複雜數學公式與 if-else 演算法決定。LLM 的機率性推論容易在小數點與分數加總上犯錯，必須完全依賴 Python 腳本的確定性運算才能給出精確值。

## 5. 預期失敗模式

- 失敗 1: LLM 擅自修改格式 (Parsing Failure)。觸發點：LLM 輸出附帶了 Markdown 解釋或忘記輸出 JSON。處理方式：validator.py 在 json.load() 階段攔截並報錯 Invalid JSON format，觸發 Hermes Agent 的自動重試。
- 失敗 2: 醫學分級判斷矛盾 (Logical Contradiction)。觸發點：LLM 自行判定病患 is_eligible: true，但抓出的數據其實算出 Child-Pugh B 級。處理方式：Python 重新計算分數，若發現違規，直接印出 Medical Rule Violation 打臉並強迫 LLM 根據錯誤原因重新思考。

## 6. 互動對象

本 Skill 屬於獨立執行的 Validation Agent，負責單次輸入的 EMR 核對與演算法把關，不與其他同學或 Pairwise Skill 互動，亦不需啟動 Hermes subagent 進行長程規劃。

## 7. Token Budget 估算

| Scenario | 預估 input tokens | 預估 output tokens | 預估 total |
|---|---:|---:|---:|
| Scenario 1 | 800 | 300 | 1100 |
| Scenario 2 | 800 | 300 | 1100 |
| Scenario 3 | 800 | 300 | 1100 |