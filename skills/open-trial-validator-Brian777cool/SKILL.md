---
name: open-trial-validator-Brian777cool
description: Advanced PLGA nanocarrier clinical trial eligibility extraction with multi-layer deterministic validation.
version: 1.0.0
metadata:
  hermes:
    tags: [medical, oncology, verification, math]
    category: medical
---

# PLGA Nanocarrier Trial Validator Skill

## When to Use
當需要評估肝癌病患是否符合「主動標靶 PLGA 奈米載體」臨床試驗收案標準時觸發。

## Procedure
1. 閱讀病歷，嚴格抽取以下原始數據，**不要自行計算分數或體積**：
   - `patient_id` (病患編號，如 P-1001)
   - `tumor_length_cm` (腫瘤最大長徑，浮點數)
   - `tumor_width_cm` (腫瘤最大垂直寬徑，浮點數)
   - `platelet_count` (血小板數量，整數)
   - `bilirubin` (總膽紅素 mg/dL，浮點數)
   - `albumin` (白蛋白 g/dL，浮點數)
   - `inr` (凝血酶原時間，浮點數)
   - `ascites` (腹水狀態，僅限 "none", "mild", "severe")
   - `encephalopathy` (肝性腦病變，僅限 "none", "grade 1", "grade 2", "grade 3", "grade 4")
2. 將抽取的數據與 `task_id` 寫成一個純 JSON 檔案，存為 `temp_extract.json`。
3. 執行指令：`python scripts/validator.py temp_extract.json`。
4. **重點**：如果腳本回報「Hallucination detected」或「Medical Rule Violation」，請仔細閱讀錯誤訊息，修正你抽取的數值後重新執行腳本（最多重試 3 次）。
5. 若腳本回報 "Validation Passed!"，請直接將腳本吐出的 ````json 區塊完整複製，作為你最後一個動作的輸出。

## Pitfalls
- 試圖自行計算 Child-Pugh 分數或腫瘤體積，導致幻覺與數學錯誤。
- 捏造病歷上沒有的血小板數據，未與 EMR 資料庫核對。

## Verification
最終輸出必須嚴格依照 `validator.py` 驗證過關後所提供的 JSON 格式輸出，不可遺漏由 Python 腳本計算出的 `calculated_tumor_volume_cm3` 與 `calculated_cp_class` 欄位。