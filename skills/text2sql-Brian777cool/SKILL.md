---
name: text2sql-Brian777cool
description: Converts natural language to SQLite queries and verifies them against an in-memory database.
version: 1.0.0
metadata:
  hermes:
    tags: [sql, database, verification]
    category: data
---

# Text-to-SQL Validator Skill

## When to Use
當使用者給定一段自然語言（例如：「幫我找出薪水超過五萬的員工」），要求轉換為 SQL 查詢語法時觸發。

## Procedure
1. 分析使用者的自然語言需求。
2. 根據以下唯一的資料庫結構 (Schema) 撰寫 SQLite 語法：
   - Table: `employees`
   - Columns: `emp_id` (INTEGER), `name` (TEXT), `department` (TEXT), `salary` (INTEGER), `hire_date` (DATE)
3. 將你的結果寫成 JSON 格式，包含 `task_id` 與 `generated_sql` 兩個欄位，並儲存為 `temp_sql.json`。
   - 注意：`generated_sql` 必須是純 SQL 字串，不可包含 markdown 標記（如 ```sql）。
4. 呼叫並執行 `python scripts/validate_sql.py temp_sql.json`。
5. **如果腳本回報 `SQLite Execution Error`**，請詳細閱讀錯誤訊息（例如你可能捏造了不存在的欄位），修正你的 SQL 語法後重新執行驗證（最多重試 3 次）。
6. 如果腳本順利執行沒有報錯，請直接將腳本吐出的 ````json 區塊完整複製，作為你最後一個動作的輸出。

## Pitfalls
- 試圖查詢 Schema 中沒有的欄位（如 `age` 或 `address`）。
- SQL 語法結尾忘記加上分號，或使用了非 SQLite 支援的特規語法。

## Verification
最終輸出必須嚴格依照 `validate_sql.py` 驗證過關後所提供的 JSON 格式輸出，且必須包含腳本自動幫你加上的 `execution_status` 與 `query_results` 欄位。