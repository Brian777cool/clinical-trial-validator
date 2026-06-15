---
name: code-author-Brian777cool
description: Generates robust Python code based on requirements and validates syntax via AST.
version: 1.0.0
metadata:
  hermes:
    tags: [coding, python, generation]
    category: engineering
---

# Code Author Skill

## When to Use
當使用者給予程式設計需求，要求你撰寫一段 Python 程式碼時觸發。

## Procedure
1. 仔細閱讀使用者的程式開發需求與邊界條件。
2. 撰寫符合需求且具備良好註解的 Python 程式碼。
3. 將結果寫成純 JSON 格式，包含 `task_id` 與 `generated_code` 兩個欄位，儲存為 `temp_code.json`。
   - 注意：`generated_code` 必須是純字串，請正確處理換行符號 (`\n`)，**絕對不可**在字串開頭加上 ```python 等 Markdown 標記。
4. 執行指令：`python scripts/validator.py temp_code.json`。
5. **如果腳本回報 `Syntax Error`**，代表你生成的程式碼有縮排錯誤或語法瑕疵，請修正後重新執行驗證（最多重試 3 次）。
6. 驗證通過後，直接將腳本輸出的 ````json 區塊完整複製，作為最終輸出。

## Pitfalls
- 忘記 `import` 必要的標準函式庫。
- 在 `generated_code` 中混入人類自然語言的解釋，導致 AST 解析失敗。

## Verification
最終輸出必須嚴格依照 `validator.py` 驗證過關後所提供的 JSON 格式輸出，確保程式碼具備基礎的執行合法性。