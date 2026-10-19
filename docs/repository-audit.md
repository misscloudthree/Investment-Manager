# Repository Audit — 第一階段

檢查範圍：根目錄、AGENTS.md、README.md、docs/、.agents/skills/、src/、tests/、config/、data/ 與 .github/workflows/。本次任務基線提交為 `5e2accd`；檢查時已有上一個尚未提交工作的兩個 Skill、AGENTS 與共用資料契約修改，本次納入重整，未重設使用者工作。

| 區域 | 基線事實 | 本次處理／限制 |
|---|---|---|
| README.md | 只有專案名稱 | 增加定位、文件導覽與契約檢查方式 |
| AGENTS.md | 原為待補指引；工作區已有研究規則 | 要求先讀 PROJECT，禁止 AI 修改核准 thesis／實際持倉及自動交易 |
| 六個 SKILL.md | 已提交版本均只有標題與待補文字，無 frontmatter／契約／可執行工具 | 完成兩個設計；其餘四個保留佔位並在 PROJECT 清楚列狀態 |
| docs/ | 已提交版本只有 .gitkeep | 新增專案規格、資料契約、原始來源、串接與本稽核 |
| src/ | 只有 .gitkeep | 不假造資料服務或研究引擎；第一階段不建立自動化 |
| tests/ | 只有 .gitkeep | 新增 JSON 契約與文件連結／來源追溯靜態驗證 |
| config/、data/、workflows/ | 只有 .gitkeep | 無設定、資料、CI 或排程；本次不部署 |

未找到執行環境版本鎖定、API adapter、財務計算程式、資料庫、核准系統、交易程式或現成測試。GitHub 參考儲存庫以 HTTPS 唯讀下載至 `/tmp/investment-skill-references`，只讀文字與授權檔；沒有安裝其依賴、執行工具或 hooks。本次未向金融 API 提供憑證，也未驗證即時行情或研究報酬。

## 驗證結果

在隔離的 Python 3.12 venv 安裝 `requirements-dev.txt` 後執行：

```sh
python -m unittest discover -s tests -v
git diff --check
```

22 項測試通過，涵蓋五份 Schema 定義、四份合成輸入輸出、無效日期、字串代碼、缺值、來源要求、排名／分數限制、ETF／公司路徑隔離、草稿不得聲稱已核准、三情境名稱、文件連結與固定 commit 來源。diff 空白檢查通過。首次測試發現系統預裝 jsonschema 缺少可選日期格式依賴，已在開發依賴明列 `format-nongpl` 並在乾淨 venv 重測通過；沒有放寬日期測試。

三份 MIT notice 與下載來源 LICENSE 的 SHA-256 相同。測試不會連金融 API，不使用真實持倉，沒有實作與驗證估值計算、研究訊號績效或每日監控。Schema 不能取代來源可信度、計算正確性、跨欄位語義及人工核准檢查；剩餘工作與驗收標準見 PROJECT。

