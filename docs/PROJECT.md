# AI Investment Manager 專案規格

狀態：Task 1 基礎已建立，Task 2 進行互動研究交接與提案驗證；尚未具備真實資料接入、研究引擎或排程能力。本文為未來任務的首要專案規格。研究市場為台灣上市／上櫃股票與台灣掛牌 ETF，報告繁體中文、時間 Asia/Taipei、基準幣別 TWD（可指定且須換匯依據）。

## 目標與非目標

以 Investment Thesis 為核心：主動發掘候選、深度研究、保存使用者認可的理由／KPI／估值與風險條件、每日觀察新證據、評估穿透曝險，只在重要變化時請使用者重評。

成功不是短線股價預測或產生大量警報，而是讓每個投資理由可查證、可追蹤、可反駁、可追溯至核准版本。系統不自動下單，不直接連接交易執行接口；AI 不得修改已核准假設、實際持倉或假造交易。第一階段不建置全自動投資平台、歷史績效宣稱或最佳化配置模型。

## 已確認的混合架構（Task 2）

- ChatGPT：依 GitHub canonical Skills 互動研究、質性分析與決策支援；不假設它會自動收到 Codex Skills 或能讀私有 Repository。
- GitHub：Skills、Schema、規格與未來已核准投資紀錄的 Single Source of Truth。敏感批准紀錄須在 Task 3 確認私有／受控 Repository 與權限；本 Task 不寫批准紀錄，公開 repo 不放私人持倉或金鑰。
- Codex：開發、更新與驗證方法及軟體；Python：確定性驗證、計算及未來監控；GitHub Actions：未來排程。
- Human Investor：投資決策最終權限。ChatGPT／Codex 不自動批准或交易。

Task 2 聚焦方法整合、Memo、Thesis Proposal 與 ChatGPT Mode A/B 交接，不建立自動研究引擎或排程篩選。Task 3 才落實核准、持久化、每日監控與組合風險；Task 1 的整體架構與長期規格保留。

## 兩個邏輯 Agent

這裡的 Agent 是未來工作流程角色，不代表已部署服務，也不要求目前啟動多代理。

| 角色 | 觸發 | 流程 | 產物與人工介面 |
|---|---|---|---|
| Agent 01 — Investment Discovery & Research | 手動／未來每月排程 | 主檔與可用性檢查 → Opportunity Screener → 分開的股票／ETF 候選 → Company Research／ETF 分支 → 結構化 Investment Memo | 候選清單、證據與估值假設；由使用者決定加入觀察清單、候選配置或提交投資假設更新 |
| Agent 02 — Investment Monitoring & Risk | 手動／未來每日排程 | 讀取核准 thesis 版本與實際持倉快照 → 取最新可驗證證據 → 事件去重與關聯 → Thesis Health → Macro/Industry Risk → Portfolio Risk | Daily Investment Brief、證據缺口、重大警示與變更提案；不得自行更新核准基線 |

每日時點待決，必須配合台灣收盤、公告延遲及海外資產 NAV 時差。無交易日不假造行情；重要公告仍可按公告時間處理。

## 六個 Skills 邊界

| Skill | 工作 | 本階段狀態 |
|---|---|---|
| opportunity-screener | 驗證母體、品質閘門、多因子排序；ETF 獨立適配檢查 | 完整方法與 JSON 契約；未接資料／計算執行器 |
| company-research | 公司財務／生意／治理／估值、ETF 基金盡職調查、Memo／kill criteria | 完整方法與 JSON 契約；未接資料／計算執行器 |
| thesis-monitor | 核准 KPI／失效條件逐項對照最新證據，區分價格噪音與假設變化 | 既有檔仍為佔位，僅本文件定義介面與目標 |
| macro-industry-risk | 以因果傳導把總經／產業事件映射至 thesis 與曝險 | 既有檔仍為佔位，尚未實作 |
| portfolio-risk | 以實際市值及 ETF 穿透評估集中、重疊、流動性與情境風險 | 既有檔仍為佔位，尚未實作 |
| decision-recorder | 變更提案、明確核准、追加版本與審計事件 | 既有檔仍為佔位；尚無權限／儲存後端 |

## 資料流程與責任

```text
官方／授權資料 → 原始快照（不可變、來源／公告／擷取時間）
               → 正規化（身分、幣別、單位、季度、公司行動）
               → 品質閘門 → 版本化證據與計算 → 篩選／研究草稿
               → 使用者核准 → 核准 Thesis Registry
核准 thesis + 持倉快照 + 新事件 → 監控／曝險 → 去重警示／Daily Brief
                                          → 變更提案 → 使用者核准 → 新版本
```

來源、計算與缺值規則在 `research-data-contract.md`。原始資料與使用者私有狀態不直接存進 Git；API 憑證只由執行環境注入。`schemas/` 定義的是研究交換契約，不是 API 已實作的證明。`docs/reports/` 只放可公開／匿名資料；敏感研究及持倉輸出至指定私有儲存位置。

至少保存以下邏輯實體（持久化後端下一階段選定）：

- Instrument：代碼、交易所、資產類型與幣別；ETF 另含底層／策略。
- Evidence：來源、URL／文件定位、資料期間、公開／擷取時間、內容版本與品質；事實／推論／假設／未知分開。
- ResearchRun：run_id、截止時間、版本、輸入、資料覆蓋、輸出、失敗／缺口。
- ThesisVersion：thesis_id、version、parent_version、instrument、投資理由、3–5 個 KPI、估值假設、風險／kill criteria、觀察頻率、建立者與核准者／時間、決策證據。
- PortfolioSnapshot：snapshot_id、effective_at、來源／確認者、實際股數／現金、幣別、估值日期；成本與當前市值分開。候選配置不能寫成實際持倉。
- Event／Assessment／Alert：canonical_event_id、source_event_ids、事件版本、公告時間、受影響 thesis/KPI、風險因子、首次／最近觀察、重要性、去重鍵與確認狀態。

## 決策與核准狀態機

`draft → proposed → approved | rejected`。已核准版本不可原地修改；新證據只新增 assessment。需改理由、門檻、估值或配置時，另建帶 `parent_version` 的 draft，再由使用者核准；核准後另記 supersession 事件標示舊版已被取代，不改舊版內容並保留全文。關閉假設同樣需核准，沒有任何 Skill 可自動繞過。

核准需明確包含：核准者、核准時間、proposal_id、被核准的確切版本／內容雜湊、父版、理由。模糊回覆、沉默、模型同意或測試 fixture 都不算核准。未來儲存層須做版本衝突檢查與原子追加；舊提案不得覆蓋新核准版本。

觀察清單、候選配置、已核准投資假設與實際持倉是四種獨立狀態。實際持倉只能從使用者明確確認的輸入／可信匯入形成新快照；AI 推薦不會創造持倉。即使使用者核准研究或配置提案，系統仍不執行交易。

研究產物的 `status=complete` 僅表示該次方法與證據檢查完成；`approval_status=draft` 永遠不等於核准 thesis。

## 監控、去重與重要性

- Thesis Health 初期採 `intact / challenged / invalidated / insufficient_data`，皆為 assessment，不改核准基線；無可靠 KPI 不產生虛構 0–100 分數。失效表示須人工重評，不等於自動賣出。
- 同一公告被多家媒體轉載，依官方公告 ID／發行者／日期／內容版本建立 canonical event；來源證據保留多筆但事件只一筆。更正公告建立新版並連回原事件。
- 一事件可同時連到宏觀、產業、個股及組合，但摘要引用同一 event_id；不可把同一匯率衝擊在各 Skill 分數加總成多次獨立損失。情境計算需列因子相依與共同假設，不加總互斥情境。
- 重大事件：事先核准的 KPI／kill 門檻觸發、重大治理／法規或交易狀態變化、核准曝險限額突破、關鍵資料失效致無法監控。以重要性與新證據決定通知；單純跌價非 thesis 失效。
- 無重要變化時 Daily Brief 記錄「未發現可驗證重大變化」、覆蓋範圍與缺口，不要求使用者反覆核准。無資料時不能稱無風險。
- 警示去重鍵規劃為 `(thesis_version, canonical_event_id, rule_id, severity)`；相同事件無新證據／嚴重度變化不重發，重大更正／升級可重開。冷卻期、通知渠道及延遲容許值待使用者決定。

## 第一階段成功標準

1. 未來任務能從本文件、AGENTS 與來源紀錄理解邊界，不將佔位 Skill 視為可執行能力。
2. 兩個優先 Skill 有輸入／輸出 JSON Schema、股票／ETF 不同方法、來源／日期／缺值／計算／風險／報告規則。
3. 契約測試接受明示合成的合理輸入，拒絕錯誤商品、漏來源、缺值假裝分數、ETF 混用公司估值與草稿冒充核准等錯誤。
4. 上游版本與 MIT 授權可追溯；不執行第三方未知程式；不臆測未公開的 XVARY 權重。
5. 真實資料未串接前，明確標示只能做規格與契約驗證，不聲稱投資研究績效或即時監控已上線。

## 未來運行驗收（本次尚未達成）

- 官方主檔與少量具代表性的上市／上櫃、金融／非金融、股票型／債券／跨境／主動式 ETF 實際取數、來源核對與可重算報告。
- Python 計算模組通過季度差分、單位換算、負分母、公司行動、TD/TE、DCF／敏感性及資料日期邊界測試。
- 核准狀態機、不可變歷史、衝突控制與私密儲存測試；AI 無交易權限。
- 每日重跑相同事件不重發警示；真正更新可觸發；資料中斷顯示缺口而非低風險。
- 用事先標記的歷史案例驗證事件對應與人工重評品質；篩選權重須另做避免前視／存活者偏誤的研究，未完成前不聲稱有效 alpha。

## 後續順序與待決事項

1. 確認市場範圍、基準、投資期間、風險限額與資料預算；依 `api-integration.md` 選來源、授權、存取限制與 refresh SLA。
2. 實作正規化資料層及可測試 Python 計算；以匿名／公開樣本走通兩個 Skill，保留真實驗證結果。
3. 定義 thesis／portfolio／event 的正式 schemas 與私有儲存，落實使用者核准和版本控制；目前兩個研究契約不能取代核准後端。
4. 完成其餘四個 Skill，驗證事件去重、組合穿透及警示規則；再接排程與 Daily Brief。
5. 通知管道、冷卻／升級規則、資料留存／刪除、持倉匯入方式與權限待決。未選定前不部署或傳送私人資料。


## Task 2 交付與下一階段

canonical 方法仍在兩個 SKILL.md；ETF 留在隔離分支，決策理由見 `TASK2_AUDIT.md`。`SKILL_MANIFEST.json` 記錄方法 revision、依賴與檔案 hash，Git commit 在實際 bundle／研究時解析，不把 HEAD 字樣當版本。交接與收件流程見 `CHATGPT_HANDOFF.md`，輸出使用 `INVESTMENT_MEMO_TEMPLATE.md` 及唯一 `schemas/thesis-proposal.schema.json`。既有研究工作表 Schema 保留相容，不能充當已核准 thesis。

Task 2 成功：離線 bundle 可重現、缺依賴／版本漂移可拒絕、stock／ETF mock 提案與錯誤案例通過／被拒，使用者有第一檔 ChatGPT 手動測試步驟。這些不等於真實金融分析或 live ChatGPT acceptance；尚須實際工具、官方資料與人工驗證。

接續順序調整：先以 ChatGPT 測試一檔股票及 ETF 的方法載入、來源品質與輸出，記錄真實驗證結果；依需求再做小型 Python 計算與資料 adapter，而非先建全自動研究平台。Task 3 才設計權限、批准版本與私有儲存，之後才接每日事件、去重、風險和排程。舊 `agent-implementation-prompt.md` 為歷史候選開發清單，不覆蓋本階段範圍。


## Task 2.1 決策品質升級

研究的成功標準增加「現在是否值得投入、為什麼、何時應改變決定」；三閘門、ETF 底層報酬情境與反方方法仍以 canonical company-research 為準，不能只交產品介紹。Proposal 2.0 增必要 investment_decision，Memo 最後呈現同一決策。缺證據可交 Insufficient Evidence，但必須列取得決定性資料的方法。

TASK21_DECISION_REVIEW.md 記錄設計根因與執行責任的證據限制。Mock 100 萬／五年／0050、00646、00713 僅測契約與降級，不等於真實 ETF 評等。Task 3 還未實作，新增穩定 condition_id、既有 kpi_id／source_id 與未核准狀態供後續保存／監控，不更改既有核准紀錄。真正研究仍需官方資料、模型適用性與人工審查。
