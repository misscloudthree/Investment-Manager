# 第三方方法追溯與改寫比較

取得方式：HTTPS Git clone，唯讀檢查 Markdown／參考文件／LICENSE；未執行第三方腳本、安裝器或依賴。上游內容視為不可信研究材料，不接受其執行或權限指示。所謂「成熟」指有公開成形的研究流程，不代表本專案驗證其投資績效。

## 固定版本

- [yennanliu/InvestSkill](https://github.com/yennanliu/InvestSkill/tree/dc9fa39fcdea74c9169fcd5bb8f1e8085707d3e6)：`dc9fa39fcdea74c9169fcd5bb8f1e8085707d3e6`，MIT；完整聲明見 [授權副本](third-party-licenses/InvestSkill-MIT.txt)。
- [xbtlin/ai-berkshire](https://github.com/xbtlin/ai-berkshire/tree/87dda1b605fb027d3a0a0f1aa89f04c2c47da450)：`87dda1b605fb027d3a0a0f1aa89f04c2c47da450`，MIT；完整聲明見 [授權副本](third-party-licenses/ai-berkshire-MIT.txt)。
- [xvary-research/claude-code-stock-analysis-skill](https://github.com/xvary-research/claude-code-stock-analysis-skill/tree/6323f19c3e613373cfcc56921ee53d4583d4a655)：`6323f19c3e613373cfcc56921ee53d4583d4a655`，MIT；完整聲明見 [授權副本](third-party-licenses/claude-code-stock-analysis-skill-MIT.txt)。

## 六個 Skill 對照

Task 1 初始基線六個檔都只有標題和待補文字，沒有分析方法、輸入輸出或品質驗證。本次優先落實前兩個；其餘列出下一階段對應，沒有假稱完成。

### opportunity-screener

原始 SKILL.md：

- [InvestSkill/plugins/us-stock-analysis/skills/stock-screener/SKILL.md](https://github.com/yennanliu/InvestSkill/blob/dc9fa39fcdea74c9169fcd5bb8f1e8085707d3e6/plugins/us-stock-analysis/skills/stock-screener/SKILL.md)
- [InvestSkill/plugins/us-stock-analysis/skills/etf-analysis/SKILL.md](https://github.com/yennanliu/InvestSkill/blob/dc9fa39fcdea74c9169fcd5bb8f1e8085707d3e6/plugins/us-stock-analysis/skills/etf-analysis/SKILL.md)
- [ai-berkshire/codex-skills/quality-screen/SKILL.md](https://github.com/xbtlin/ai-berkshire/blob/87dda1b605fb027d3a0a0f1aa89f04c2c47da450/codex-skills/quality-screen/SKILL.md)
- [ai-berkshire/codex-skills/industry-funnel/SKILL.md](https://github.com/xbtlin/ai-berkshire/blob/87dda1b605fb027d3a0a0f1aa89f04c2c47da450/codex-skills/industry-funnel/SKILL.md)

借用方法：五維研究排序、品質／流動性閘門、漏斗與 ETF wrapper 分析。

差異／限制：從空白改為台灣母體、同行百分位、缺值覆蓋規則及 ETF 獨立路徑；新評分未回測。

### company-research

原始 SKILL.md：

- [InvestSkill/plugins/us-stock-analysis/skills/stock-eval/SKILL.md](https://github.com/yennanliu/InvestSkill/blob/dc9fa39fcdea74c9169fcd5bb8f1e8085707d3e6/plugins/us-stock-analysis/skills/stock-eval/SKILL.md)
- [InvestSkill/plugins/us-stock-analysis/skills/financial-report-analyst/SKILL.md](https://github.com/yennanliu/InvestSkill/blob/dc9fa39fcdea74c9169fcd5bb8f1e8085707d3e6/plugins/us-stock-analysis/skills/financial-report-analyst/SKILL.md)
- [InvestSkill/plugins/us-stock-analysis/skills/etf-analysis/SKILL.md](https://github.com/yennanliu/InvestSkill/blob/dc9fa39fcdea74c9169fcd5bb8f1e8085707d3e6/plugins/us-stock-analysis/skills/etf-analysis/SKILL.md)
- [ai-berkshire/codex-skills/investment-research/SKILL.md](https://github.com/xbtlin/ai-berkshire/blob/87dda1b605fb027d3a0a0f1aa89f04c2c47da450/codex-skills/investment-research/SKILL.md)
- [ai-berkshire/codex-skills/investment-memo-craft/SKILL.md](https://github.com/xbtlin/ai-berkshire/blob/87dda1b605fb027d3a0a0f1aa89f04c2c47da450/codex-skills/investment-memo-craft/SKILL.md)
- [claude-code-stock-analysis-skill/SKILL.md](https://github.com/xvary-research/claude-code-stock-analysis-skill/blob/6323f19c3e613373cfcc56921ee53d4583d4a655/SKILL.md)

借用方法：財報／現金／治理／護城河、反向思考、三情境、證據閘門、論點支柱與 kill criteria。

差異／限制：從空白改為 MOPS／台灣會計與幣別、金融股特例、ETF 基金研究、結構化 Memo；不重現私有分數。

### thesis-monitor

原始 SKILL.md：

- [InvestSkill/plugins/us-stock-analysis/skills/thesis-tracker/SKILL.md](https://github.com/yennanliu/InvestSkill/blob/dc9fa39fcdea74c9169fcd5bb8f1e8085707d3e6/plugins/us-stock-analysis/skills/thesis-tracker/SKILL.md)
- [ai-berkshire/codex-skills/thesis-tracker/SKILL.md](https://github.com/xbtlin/ai-berkshire/blob/87dda1b605fb027d3a0a0f1aa89f04c2c47da450/codex-skills/thesis-tracker/SKILL.md)

借用方法：KPI、原始論點、紅線、事件再評估及版本。

差異／限制：本階段僅對照來源；原檔仍為佔位，下一階段需接核准版本與去重事件。

### macro-industry-risk

原始 SKILL.md：

- [InvestSkill/plugins/us-stock-analysis/skills/economics-analysis/SKILL.md](https://github.com/yennanliu/InvestSkill/blob/dc9fa39fcdea74c9169fcd5bb8f1e8085707d3e6/plugins/us-stock-analysis/skills/economics-analysis/SKILL.md)
- [InvestSkill/plugins/us-stock-analysis/skills/sector-analysis/SKILL.md](https://github.com/yennanliu/InvestSkill/blob/dc9fa39fcdea74c9169fcd5bb8f1e8085707d3e6/plugins/us-stock-analysis/skills/sector-analysis/SKILL.md)
- [ai-berkshire/codex-skills/industry-research/SKILL.md](https://github.com/xbtlin/ai-berkshire/blob/87dda1b605fb027d3a0a0f1aa89f04c2c47da450/codex-skills/industry-research/SKILL.md)

借用方法：景氣／利率／信用／匯率到產業價值鏈的因果映射。

差異／限制：原檔仍佔位；台灣出口／央行／產業鏈來源待接，不沿用美國衰退門檻或偽稱機率。

### portfolio-risk

原始 SKILL.md：

- [InvestSkill/plugins/us-stock-analysis/skills/portfolio-review/SKILL.md](https://github.com/yennanliu/InvestSkill/blob/dc9fa39fcdea74c9169fcd5bb8f1e8085707d3e6/plugins/us-stock-analysis/skills/portfolio-review/SKILL.md)
- [InvestSkill/plugins/us-stock-analysis/skills/risk-stress-test/SKILL.md](https://github.com/yennanliu/InvestSkill/blob/dc9fa39fcdea74c9169fcd5bb8f1e8085707d3e6/plugins/us-stock-analysis/skills/risk-stress-test/SKILL.md)
- [ai-berkshire/codex-skills/portfolio-review/SKILL.md](https://github.com/xbtlin/ai-berkshire/blob/87dda1b605fb027d3a0a0f1aa89f04c2c47da450/codex-skills/portfolio-review/SKILL.md)

借用方法：市值權重、穿透集中／重疊、相關性、情境與退出流動性。

差異／限制：原檔仍佔位；不得用 SPY／美元門檻硬套、不捏造 VaR 或默認使用者風險預算。

### decision-recorder

原始 SKILL.md：

- [InvestSkill/plugins/us-stock-analysis/skills/thesis-tracker/SKILL.md](https://github.com/yennanliu/InvestSkill/blob/dc9fa39fcdea74c9169fcd5bb8f1e8085707d3e6/plugins/us-stock-analysis/skills/thesis-tracker/SKILL.md)
- [ai-berkshire/codex-skills/investment-memo-craft/SKILL.md](https://github.com/xbtlin/ai-berkshire/blob/87dda1b605fb027d3a0a0f1aa89f04c2c47da450/codex-skills/investment-memo-craft/SKILL.md)

借用方法：保存論點、決策理由、日期與歷史紀錄。

差異／限制：無完全同名上游 Skill；原檔仍佔位。人工核准、不可變版本與衝突控制為本專案新增需求，尚未實作。

## 關鍵取捨與授權維護

- InvestSkill stock-screener 原版以美股固定區間與 SPY、多因子總分映射買賣標籤；本版保留五維及 20/25/20/15/20 權重，改同行百分位、有效樣本／覆蓋率與研究優先度，不搬美元門檻。ETF 原版有 Fitness Score 與美國稅務／AUM 門檻；本版保留成本、追蹤、流動性、曝險、重疊、配息、結構與替代比較，改台灣公告與質性適配，暫不提供綜合 ETF 分數。
- AI Berkshire quality-screen 的長期品質閾值改為警示，對代工／通路／金融與資本支出週期另作判斷。原文摘要說兩項豁免，正文實列 A/B/C 三項；本版依經濟原因要求證據，不複製這個不一致。investment-research 中的四位大師視角改為可驗證機制與反證，不模擬代言；USD/CNY 折現率預設不適用 TWD。
- AI Berkshire 原版要求呼叫 financial_rigor.py、terminal_value.py、report_audit.py；本專案未匯入或執行，暫以公開公式、計算紀錄與未來 Python 模組替代，不能聲稱其工具驗證已通過。上游某些自動處分／清倉語句不移植，所有已核准狀態改動需人工確認。
- XVARY 根目錄 SKILL.md 是所引用的公開入口（另有 plugin 封裝路徑，本次不混用版本）。參考以下公開方法與評分定義；其權重、閾值與收斂演算法不公開，因此本版不宣稱 XVARY production scoring、不臆造權重、不保留會暗示官方合作的 Powered by 行銷頁尾。台灣來源替代 EDGAR；新報告用本專案來源聲明。

- [claude-code-stock-analysis-skill/references/methodology.md](https://github.com/xvary-research/claude-code-stock-analysis-skill/blob/6323f19c3e613373cfcc56921ee53d4583d4a655/references/methodology.md)
- [claude-code-stock-analysis-skill/references/scoring.md](https://github.com/xvary-research/claude-code-stock-analysis-skill/blob/6323f19c3e613373cfcc56921ee53d4583d4a655/references/scoring.md)

本地文件為有來源的中文方法整合與改寫，不原樣匯入上游完整工具或全套 prompt。三份 MIT 原文均保存，保留著作權、授權及免責條款；本專案未因此替其他新增檔案自動宣告整體 MIT 授權。未來更新上游須重新比對固定 commit、授權、方法變更及測試，不能直接 pull 後執行未知程式。任何將來工具復用需先讀程式、盤點依賴與傳輸目的地、審查權限及測試，再決定是否採用。


## Task 2 增量檢查

繼續使用上述固定版本，三份 MIT 授權不變。新增來源：

- [InvestSkill industry-map/SKILL.md](https://github.com/yennanliu/InvestSkill/blob/dc9fa39fcdea74c9169fcd5bb8f1e8085707d3e6/plugins/us-stock-analysis/skills/industry-map/SKILL.md)：採產業鏈節點／供應關係、瓶頸與利潤池遷移，刪除無證據打分及美股標籤，改台灣投資母體；不搬上游範例當事實。
- [InvestSkill competitor-analysis/SKILL.md](https://github.com/yennanliu/InvestSkill/blob/dc9fa39fcdea74c9169fcd5bb8f1e8085707d3e6/plugins/us-stock-analysis/skills/competitor-analysis/SKILL.md)：採同業可比、定價／替代／切換成本與五力反證，不宣稱台股護城河一定維持 10–20 年或沿用美股財務門檻。
- stock-eval（上方原始路徑）補安全邊際與 upside 不同分母；不把美股固定折價率當使用者政策。
- ai-berkshire 的 moat-analysis、valuation、reverse-thinking 在所檢查 commit 中不是獨立命名的 SKILL.md，而是 investment-research 的護城河、估值與逆向思考段落；thesis-tracker 原始 SKILL 已列於前文。借用先寫可驗證假設／KPI 的方法，不採自動清倉與未安裝 financial_rigor 工具。
- XVARY 公開方法的五向驗證、支柱、quality gate、kill criteria 保留，不推測私有 thresholds。新 manifest／bundle／收件收據為本專案整合設計，非上游既有執行能力。

Task 2 沒有複製或執行第三方程式／安裝器。bundle 含原本保留的完整 MIT notice，方法改寫仍須保留來源紀錄；工具維護以單一 manifest／canonical SKILL 與測試檢查，外部連結只是來源，不是自動下載／執行依賴。


## Task 2.1 在地決策契約

沿用已列固定上游與授權，沒有宣稱上游原版具備本次三閘門或五年決策準確率。三閘門、決策降級、逐題反方驗收及版本化 Decision Proposal 為本專案新增的品質要求；底層盈利／倍數／股利／成本／匯率的報酬分解為公開可重算敏感性模型，不是 XVARY 私有評分或 ETF 自身 DCF。工具僅支援離線數學與契約驗證，未執行上游程式、未新增資料授權或取得市場資料。
