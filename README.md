# Investment Manager

以投資假設為核心、專注台股與台灣掛牌 ETF 的 AI Investment Manager。

目前為 **Task 2：互動研究方法與 ChatGPT 交接階段**。尚無資料 API、研究執行器、排程、核准儲存系統或交易功能；兩個完成設計的 Skill 不代表已具備真實市場分析能力。

- [專案目標與架構](docs/PROJECT.md)：未來任務先讀，定義兩個 Agent、人工核准與成功標準。
- [開發規範](AGENTS.md)、[Repository 稽核](docs/repository-audit.md)。
- [資料規則](docs/research-data-contract.md)、[結構化契約](docs/skill-contracts.md)、[第三方方法與授權](docs/skill-provenance.md)。
- [機會篩選](.agents/skills/opportunity-screener/SKILL.md)、[公司／ETF 研究](.agents/skills/company-research/SKILL.md)。其餘四個 Skill 仍為佔位。
- [資料 API 與下一步](docs/api-integration.md)。

## 契約檢查

Python 3.12；先在虛擬環境安裝開發依賴（含日期格式驗證支援）：

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

測試只驗證 Schema、合成資料與靜態文件一致性，不驗證真實行情、估值正確性、策略績效或自動監控。程式財務計算與資料接入是下一階段工作。系統不自動下單，已核准的投資假設與實際持倉必須經使用者明確確認才能形成新版本。


## 在 ChatGPT 測試研究

先看 [交接與第一檔股票操作步驟](docs/CHATGPT_HANDOFF.md)，上傳完整 bundle 或透過授權存取固定 GitHub revision，再貼 [bootstrap](docs/CHATGPT_BOOTSTRAP.md)。單一官方來源的數據仍需核對；不能把 schema-valid 當投資準確。

- [Skill Manifest](docs/SKILL_MANIFEST.json)：canonical 路徑、revision、hash、依賴、資產類型與輸入輸出。
- [Investment Memo 模板](docs/INVESTMENT_MEMO_TEMPLATE.md) 與 [Thesis Proposal Schema](schemas/thesis-proposal.schema.json)。
- [Task 2 稽核與 ETF 架構決定](docs/TASK2_AUDIT.md)。

```sh
python src/research_handoff.py check-materials
# 方法與 manifest 經審閱提交後，從該提交打包：
python src/research_handoff.py bundle --output /tmp/investment-research-skills.zip
python src/research_handoff.py verify-bundle /tmp/investment-research-skills.zip
# 驗證從 ChatGPT 下載的未核准提案：
python src/research_handoff.py validate /private/path/proposal.json --bundle /tmp/investment-research-skills.zip
```

src/research_handoff.py 只做離線封裝／契約與來源一致性檢查，不取得金融資料、不進行自動研究、不產生批准。src/run.py 是既有離線 demo，不是真實組合風險模型。只有模擬測試通過不能聲稱 ChatGPT live 研究已驗收。

下一階段先手動驗證一檔股票與 ETF 的真實研究，再在 Task 3 實作人工批准、受控持久化、每日監控與組合風險；GitHub Actions 和資料 adapter 依驗證需求逐步建置。不接券商、不自動交易。


## Task 2.1：投資決策品質

兩個 Skill 新增三道獨立閘門（產品品質／現在進場／個人組合適合度）、七題反方審查，以及 Memo 最末的 Investment Decision。新提案使用 Schema 2.0；歷史提案依原 commit 驗證。來源缺漏不能用產品故事補足或假裝適合個人。

- [根因、相容性與驗收](docs/TASK21_DECISION_REVIEW.md)
- [決策元件契約](schemas/investment-decision.schema.json)（由唯一 Proposal Schema 引用）

```sh
python -m examples.etf_decision_acceptance --output-dir /tmp/task21-mock
```

此命令須於新版方法已提交後執行，輸出三檔 mock Decision Proposals 與比較報告，不連市場或 ChatGPT、不配置資金。預期為 Insufficient Evidence；未提供的價格與預測維持 null。真實研究前依 ChatGPT Handoff 重載新版，別沿用舊包。
