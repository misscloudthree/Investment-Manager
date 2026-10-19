# Investment Manager

以投資假設為核心、專注台股與台灣掛牌 ETF 的 AI Investment Manager。

目前為**專案規格與 Skills 設計階段**。尚無資料 API、研究執行器、排程、核准儲存系統或交易功能；兩個完成設計的 Skill 不代表已具備真實市場分析能力。

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
