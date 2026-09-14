# 跨領域工程技術報告 — 智慧臨床試驗收案驗證系統 (AIASE 2026 Final Project)

> **學生**：李羿昌 / **GitHub**：Brian777cool  
> **專案類別**：個人獨立完成組  
> **核心模組**：`skills/open-trial-validator-Brian777cool`

---

## 1. 核心設計決策與架構哲學

本專案的核心架構理念在於實踐「**用確定性軟體外殼 (Deterministic Harness) 包覆機率性模型 (Probabilistic LLM)**」。在真實臨床試驗（如肝癌標靶療法）收案場景中，數據的微小失真均可能直接影響患者用藥安全性與試驗合規性。本系統藉由將自然語言特徵抽取與嚴格數值運算完全解耦，建構出兼具彈性與絕對可靠性的驗證平台：

### 1.1 Pairwise 規格對齊與合約解耦 (`PAIRWISE_ROLE.md`)
- **合約層宣告**：在 `PAIRWISE_ROLE.md` 中精確規範開發角色權責，並對齊 `dev_set/pairwise/` 下的自動化驗證流程（如 `bad_code.json` 與 `good_code.json`）。
- **設計考量**：在多模組評測流水線中，若角色邊界定義模糊或格式未遵循標準，容易造成自動化評測程式解析失敗。透過宣告單一專責角色，確保自動化體檢腳本（`verify_repo.py`）能以最低的解析開銷完成靜態驗證。

### 1.2 Open Track — 智慧臨床試驗驗證引擎 (`open-trial-validator-Brian777cool`)
- **SKILL.md 臨床稽核規範**：將 Skill 定義為不具妥協空間的收案把關者。明確給定包含實驗室檢驗值、肝功能指標與解剖學限制之收案門檻；當輸入之非結構化文字與內部邏輯產生衝突時，強制模型重新稽核原始病歷。
- **Harness 確定性驗證引擎 (`scripts/validator.py`, `app.py`)**：
  - **電子病歷動態交叉比對**：動態讀取 `mock_emr_db.csv`，強制對比受試者之血小板計數、凝血酶原時間比 (INR)、總膽紅素、血清白蛋白及肝腦病變分級，防杜單一數據源缺漏或造假。
  - **解剖學尺寸極限防呆 (Anatomical Safeguard)**：內建臨床器官物理極限檢核，若腫瘤單一維度尺寸超過 20 cm 即刻中斷流程並發出防呆攔截，杜絕單位誤植或異常極端值污染收案池。
  - **三維體積與 Child-Pugh 評級演算法**：徹底沒收 LLM 的數值計算權，改由 Python 演算法接管三維體積計算（以 $\text{cm}^3$ / cm³ 為標準單位），並精準計算 Child-Pugh 肝功能總分及分級（Class A / B / C）。
  - **互動介面與標準化數據輸出**：基於 Streamlit 打造 `app.py` 視覺化操作儀表板，搭配 `test_validator.py` 進行單元測試；通過所有檢核後，即時輸出結構化之標準成果檔案 `output_gold.json`。

---

## 2. 遭遇問題、根因分析與解決方案 (Failure Analysis)

### 失敗 1：跨層級執行之相對路徑狀態耦合
- **觸發場景**：於模組子目錄（`skills/open-trial-validator-Brian777cool/scripts`）執行單元測試時運作正常，但由專案根目錄呼叫 `run_dev.py` 進行全系統整合測試時，系統隨即拋出找不到檔案的錯誤：
  ```text
  FileNotFoundError: [Errno 2] No such file or directory: 'mock_emr_db.csv'
  Process exited with code 1
  ```
- **成因分析**：Python 使用傳統相對路徑 `open('mock_emr_db.csv')` 時，定位基準依賴於終端機啟動時的當前工作目錄（Current Working Directory, CWD）。當執行腳本的層級發生改變，相對路徑便會失效。
- **解決方案**：全面重構 `validator.py` 中的檔案定位機制，使用 `os.path.dirname(os.path.abspath(__file__))` 動態解析腳本所在的實體絕對路徑，再透過 `os.path.join` 完成檔案路徑拼接，徹底解除與執行環境目錄的耦合。
- **MAST 分類**：(3) 驗證與品質

### 失敗 2：手動維護多版本設定引發格式邊界衝突
- **觸發場景**：執行自動化體檢工具 `python verify_repo.py` 時，`PAIRWISE_ROLE.md` 因微小格式偏差導致檢查中斷：
  ```text
  === verify_repo summary ===
  passed: 25/26
  failed:
  X pairwise-role:role line missing or invalid
  ```
- **成因分析**：純文字 Markdown 或 YAML 缺乏即時的語法校驗與語義回饋。隨著規格書演進至陣列格式，而本機檢查腳本仍依賴舊式的頂格字串匹配時，人工手動維護極易因為空格縮排或漏補標記而產生跨版本相容性衝突。
- **解決方案**：
  - 在 `PAIRWISE_ROLE.md` 末端補上向後相容的頂格宣告標記，使體檢腳本順利取得 `passed: 26/26`（並輸出合格之 `verify_report.json`）。
  - 進一步將設定需求收斂至 Streamlit 前端介面（`app.py`），規劃以表單元件作為單一事實來源（Single Source of Truth），由程式自動生成兼具雙版本相容性的設定檔，徹底杜絕手動編輯產生的人為格式失誤。
- **MAST 分類**：(3) 驗證與品質

### 失敗 3：缺乏生理極限檢核導致解剖學異常數據穿透
- **觸發場景**：在早期非結構化病歷解析測試中，若輸入之長度單位混淆（例如將毫米 mm 誤填為公分 cm）或病歷出現離群極值（如腫瘤單徑長達 50 cm），系統仍照常計算體積並產出「合規收案」的結論。
- **成因分析**：初期驗證邏輯僅著重於血液檢驗數值與 Child-Pugh 分級算法，忽略了器官解剖學的物理合理性邊界（Physical Sanity Check），使得明顯偏離生理現實的數據得以繞過外殼檢驗。
- **解決方案**：在 `validator.py` 的驗證管線中前置「解剖學尺寸極限防呆機制」，硬性規範單一維度尺寸上限為 20 cm。一旦數值超出合理區間，系統立即中斷收案流程並拋出顯式防呆警告，有效阻擋異常數據污染臨床資料庫。
- **MAST 分類**：(3) 驗證與品質

---

## 3. 未來改進方向與工程拓展

- **醫學病歷結構化與標準本體對齊**：計畫引入國際醫療資訊交換標準（HL7 FHIR）規範，將非結構化臨床文字自動映射至標準臨床代碼（如 LOINC、SNOMED-CT），進一步提升特徵抽取與多院區病歷整合的精確度。
- **CI/CD 自動化持續整合管線**：規劃將本機體檢程式（`verify_repo.py`）與單元測試（`test_validator.py`）整合至 GitHub Actions CI 流程，確保未來的任何代碼推送皆能自動觸發全量回歸測試並更新 `verify_report.json`。
- **生理多維度指標融合**：評估進一步串接受試者的身體組成分析（BIA）數據，將細胞外水分比（ECW/TBW）與骨骼肌指數納入輔助評估，建構更全面的受試者健康狀態防護網。

---

## 4. 分工說明

*(個人獨立完成組，本專案之提示詞規範、Python 驗證核心、前端介面與測試腳本均由李羿昌獨立開發與整合)*

---

## 5. 引用說明

- **Streamlit Documentation** (`https://docs.streamlit.io/`)：參考官方組件架構，用於 `scripts/app.py` 之臨床收案表單開發、異常告警反饋與標準 JSON 資料匯出管線。
- **Python unittest Framework** (`https://docs.python.org/3/library/unittest.html`)：參考官方測試框架，用於 `scripts/test_validator.py` 實作解剖學 20 cm 極限尺寸過濾與 Child-Pugh 分級臨界點之單元測試。