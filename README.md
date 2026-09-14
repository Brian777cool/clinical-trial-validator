# Clinical Trial Validation System (臨床試驗智慧驗證系統)

整合電子病歷（EMR）、身體組成分析（BIA）與腫瘤幾何尺寸的智慧化臨床試驗收案自動化驗證平台。本系統透過嚴格的多維度安全檢核與解剖學防呆機制，確保受試者篩選流程的安全性與數據合規性，並自動輸出標準的 Gold JSON 驗證結果。

---

## 系統架構

```text
open-trial-validator-Brian777cool/
│
├── scripts/
│   ├── app.py              # Streamlit 互動式前端介面
│   ├── validator.py        # 核心驗證邏輯與防呆引擎（EMR、Child-Pugh、尺寸防呆）
│   ├── mock_emr_db.csv     # 模擬電子病歷資料庫
│   └── output_gold.json    # 產出之標準 Gold JSON 驗證結果
└── requirements.txt        # 專案相依套件清單
```
## 核心功能與防呆機制
多維度安全檢核：自動比對病歷資料庫，嚴格檢查血小板計數、凝血酶原時間比 (INR)、膽紅素、白蛋白及肝腦病變狀況。
解剖學防呆攔截：內建腫瘤三徑尺寸極限過濾（單一維度超過 20 cm 時自動攔截），杜絕異常輸入導致的數據失真。
生理指標自動計算：即時計算腫瘤三維幾何體積 (cm³) 與肝硬化嚴重度之 Child-Pugh 積分與分級（Class A / B / C）。
互動式網頁與標準輸出：提供直覺的操作介面，驗證通過後支援一鍵下載標準化之 output_gold.json。

## 安裝與快速啟動步驟

**安裝必要套件**：
```powershell
pip install -r requirements.txt
```
啟動互動網頁介面：

```powershell
cd skills/open-trial-validator-Brian777cool/scripts
py -m streamlit run app.py
```