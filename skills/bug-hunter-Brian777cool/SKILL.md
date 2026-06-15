---
name: bug-hunter-Brian777cool
description: Analyzes Python code to identify syntax, logical, and security bugs.
version: 1.0.0
metadata:
  hermes:
    tags: [debugging, python, analysis]
    category: engineering
---

# Bug Hunter Skill

## When to Use
當接收到一段 Python 程式碼，並被要求尋找其中的潛在錯誤（Bug）、漏洞或效能問題時觸發。

## Procedure
1. 仔細閱讀傳入的 Python 程式碼 (`source_code`)。
2. 進行多維度的靜態審查，包含但不限於：
   - **Syntax & Runtime Errors**: 變數未定義、IndexError 邊界錯誤、型別不匹配。
   - **Logical Bugs**: 演算法邏輯瑕疵、無窮迴圈、不正確的條件判斷。
   - **Security & Best Practices**: 密碼明文、未處理的 Exception、效能極差的寫法。
3. 如果發現錯誤，請詳細說明錯誤原因與發生的行數。
4. 將審查結果寫成純 JSON 格式，包含 `task_id`、`has_bug` (boolean)、與 `bug_description` 欄位，存為 `temp_bug_report.json`。
   - 注意：`bug_description` 必須為字串，若無 bug 則填寫 "No obvious bugs found."。
5. 執行指令：`python scripts/validator.py temp_bug_report.json`。
6. 驗證通過後，直接將腳本輸出的 ````json 區塊完整複製，作為最終輸出。

## Pitfalls
- 產生出無效的 JSON 格式，導致後續流程崩潰。
- 回報了錯誤的行數，或是將正確的程式碼誤判為 Bug。

## Verification
最終輸出必須嚴格依照 `validator.py` 驗證過關後所提供的 JSON 格式輸出，確保判斷結果可被系統正確解析。