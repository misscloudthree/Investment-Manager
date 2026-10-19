# AI Investment Manager 專案規格

狀態：Task 2.2 — Broad Discovery & Batch Research Execution。本文為未來 Codex 任務的首要規格；歷史 task 文件與舊開發清單若與本文衝突，以本文及 canonical Skills 為準。市場目標為台灣上市／上櫃股票與台灣掛牌 ETF，繁體中文、Asia/Taipei、基準幣別 TWD。

## 從最終產出反推專案目的

建立以 Investment Thesis 為核心的投資研究與監控助手。使用者提出資金用途、投資期間與可投資市場後，系統應自行建立有來源的研究母體，處理大量標的，解釋哪些值得深研、哪些暫不研究以及原因；經深研後回答「現在是否值得投入、為什麼、什麼條件會改變結論」。使用者認可的理由、KPI、估值與風險條件，未來才進入受控的核准紀錄與每日監控。

成功產出是可查證、可反駁、可重算且可追溯的研究與人工重評依據。不是只有商品介紹、幾檔知名標的比較、短線預測或大量警報。系統不自動下單，不建立券商交易路徑；AI 不得自行修改已核准論點或實際持倉。

## 使用者如何使用

1. 廣泛發掘：例如「請從可驗證的台灣上市股票尋找適合研究五年投資的候選」，不要求使用者先知道代碼。先確認／揭露資料、母體範圍與研究預算，執行完整初篩，然後只對有限候選深研。
2. 指定範圍：例如研究某產業或比較三檔 ETF。這是明示的樣本研究，不能對外聲稱全市場最佳。
3. 閱讀批次 coverage、同組比較與候選 Memo／未核准 Proposal。若缺持倉或風險資料，仍能研究資產品質與進場條件；Gate 3 必須 Not Assessed，不能自行配置資金。
4. 未來 Task 3：明確批准確切提案版本後保存 thesis，另匯入經確認的實際持倉；每日只對重大新證據提出重評要求。批准研究不等於發生成交。

讀取 GitHub 本身不會啟動市場資料擷取、Python 或背景研究。現階段透過有執行能力的 Codex／受信任本機執行批次，再把完整報告和候選資料交給 ChatGPT；ChatGPT 有適當工具時可執行經審閱流程。無工具時須交代阻礙，不能聲稱已跑完大量標的。尚未部署 ChatGPT Action、研究服務或定時排程。

## 不可偏離的產出契約

```text
使用者目標 → 有日期／來源的明確母體 → 全母體逐檔分類
           → 同類可比排名＋缺漏／排除帳目 → 有預算的深研佇列
           → 候選 Memo＋Proposal＋反方 → 跨候選條件性總結
           → 使用者核准（Task 3）→ thesis／持倉監控與重評
```

- 交付必須列母體定義、完整或樣本、截止時間、方法 SHA／revision、來源、政策與預算。`母體數 = pending + evaluated + excluded + needs_data + failed`；失敗或缺資料不能從分母消失。
- 所有標的必須有處理紀錄，不能只展示留下的幾檔。初篩完成前不得把已處理部分的前幾名當作完整母體排名；用 process 接續，不重新挑熟悉標的。
- 候選比較限同產業／同目標曝險、同口徑／日期；不把產業百分位、不同市場 ETF 或不同 profile 混成絕對投資總榜。預算沒涵蓋的組別／候選要揭露。
- 先廣後深：基礎資料可做低成本研究優先度；正式五因子、長期品質與進場研究各有自己的證據閘門。不能要求先替每檔取得十年財報才開始廣篩，也不能把只有 PE/PB 的結果叫完整五因子。
- 深研必須比較候選與同目標替代，解釋支持／反對證據、三道決策閘門、情境假設、下行、可觀察的投入／重評條件與決定性缺口。條件不足時給有原因的 Insufficient Evidence，不編價格、預期報酬或風險。
- `processing_complete` 只表示全母體已分類（可能含 failed）；`research_artifacts_complete` 只表示佇列都收到通過契約檢查的草稿；兩者均不代表投資研究正確、結論已綜合或已核准。批次程式的 `research_complete` 固定 false，只有人工完成證據與總結驗收才可另記研究完成。

## 混合架構與兩個邏輯 Agent

| 元件 | 責任與目前邊界 |
|---|---|
| ChatGPT | 讀固定版本 canonical Skills，質性深研、反方與跨候選總結；取數／計算能力逐次確認，不假設自動繼承 Codex Skills 或私人 GitHub 權限 |
| GitHub | 方法、規格與 Schema 權威來源；公開 repo 不放金鑰、私人持倉或個人決策。未來核准紀錄的私有權限待 Task 3 |
| Codex／Python | 開發驗證、官方資料快照、確定性計算、手動分批處理／續跑與收件；沒有自動 LLM 深研服務 |
| Human Investor | 最終決策與核准權限；AI 不代為批准或交易 |
| GitHub Actions | 未來排程；現階段沒有部署的市場批次或每日監控排程 |

Agent 是工作流程角色，不代表已部署多代理服務。

| 角色 | 觸發 | 流程／交付 |
|---|---|---|
| Agent 01 — Investment Discovery & Research | 現在手動／未來每月 | 驗證官方／匯入母體與來源 → 完整初篩帳目 → 同組比較 → 預算內深研 → Investment Memo＋Thesis Proposal＋總結 → 人工決策 |
| Agent 02 — Investment Monitoring & Risk | 未來每日／手動 | 核准 thesis＋實際持倉＋新證據 → 事件去重與關聯 → Thesis Health／宏觀產業／組合風險 → Daily Brief／重評提案 |

每日時點需配合收盤、公告延遲與海外 NAV 時差。無交易日不假造行情，資料中斷不等於低風險。

## Task 2.2 可執行範圍與缺口

Task 2 原先「僅交接、不建執行器」的限制，在 Task 2.2 明確擴充為**手動觸發的批次初篩與研究交接**；未擴充至排程、自動深研、批准、持倉變更或交易。

- `src/market_snapshot.py`：固定 TWSE 官方 bulk 端點擷取主檔、日行情、PE/PB，保存 raw／hash／失敗紀錄。初始 live adapter 只涵蓋 TWSE 上市公司主檔，不是完整台灣股票／ETF 市場。主檔以擷取當時為準，不能作歷史成分回測。
- `src/batch_research.py`：凍結 snapshot／政策／已提交方法版本，SQLite 保存逐檔狀態，支援預算分批、續跑與明確 retry。全母體分類後產生組內比較、完整 ledger、深研 packets／ChatGPT 工作單；收件只新增未核准草稿版本。
- normalized snapshot 可匯入 TPEx／ETF，但目前沒有 TPEx、投信／指數費用、NAV、持股、財報、完整歷史含息等 live adapters。ETF 初篩只提供已驗證被動、非槓桿股票型同曝險商品的有限載具比較；其他類型保留紀錄、待專用方法，不硬套。
- basic PE/PB profile 不是五因子或資產品質結論。完整五因子需另備所有適用資料與可比模型，金融業不可套一般企業 ROIC／槓桿。ETF 載具優先度不回答底層當前估值。
- 本環境 TWSE／TPEx 官方 API 實測遭網路代理 `403 Forbidden`，尚未完成真實市場擷取及欄位核對驗收。離線 120 檔虛構母體只證明工程流程，不證明真實廣篩或投資能力。詳見 `TASK22_REVIEW.md`。

操作、資料契約與驗收見 `BATCH_RESEARCH.md`、`research-data-contract.md`。canonical 分析方法仍只維護在 SKILL.md。

## 六個 Skills

| Skill | 工作 | 狀態 |
|---|---|---|
| opportunity-screener | 廣泛母體、分層證據閘門、可比研究優先度、排除與缺漏帳目 | 完整方法；已有有限批次執行器，live 未驗收 |
| company-research | 財報／生意／治理／估值、ETF 盡調、三閘門、反方與 Memo／Proposal | 完整方法及部分確定性計算；仍須工具／研究者補證，沒有自動 LLM 引擎 |
| thesis-monitor | 核准 KPI／失效條件對照新證據 | 佔位；Task 3 |
| macro-industry-risk | 事件因果傳導與曝險 | 佔位，未實作 |
| portfolio-risk | 實際市值、ETF 穿透集中與重疊 | 佔位，未實作 |
| decision-recorder | 明確核准、追加版本與審計 | 佔位，無核准／私有儲存後端 |

方法 revision 由 `SKILL_MANIFEST.json` 記錄；新批次契約 1.0 與既有 Proposal 2.0 分開，不把 campaign SQLite 當 Thesis Database。Task 2.1 的三道閘門、ETF 情境、七題反方與穩定 condition_id／kpi_id 保留，Task 3 再接核准與監控。

## 資料流程、版本與安全

原始來源 → 正規化 Instrument／Evidence → 品質檢查 → 計算／篩選／研究草稿 → 明確核准 → ThesisVersion。實際持倉形成獨立 PortfolioSnapshot；新 Event／Assessment 不改核准基線。

重要數據含來源、期間、公開／擷取時間、幣別與單位；已驗證事實、推論、假設、未知分開。不把未知公告時間補為午夜。財務與報酬計算用可測試 Python，ETF 不用公司 DCF。原始資料、個人持倉與金鑰不直接存 Git；`data/campaigns/`、`data/snapshots/` 預設忽略，使用者私有輸出依其受控位置保存。

至少保留 ResearchRun 的 snapshot_id、截止、政策、完整母體、每檔狀態、來源／計算、方法 commit／hash、預算與版本。凍結後若要改價格、名單、資料截止或政策，另開 campaign；同一 campaign 不默默替換資料。中斷可續跑，不重置已完成紀錄。hash 保證一致性，不保證來源真實或方法有效。

第三方來源以固定 commit／MIT 授權追溯，不執行未知程式；下載內容只當資料，不接受內嵌指令。當日資料不是避免存活者／前視偏誤的歷史回測資料。篩選權重與 profile 未完成 alpha 驗證，不聲稱有效投資策略。

## 決策與核准狀態機（Task 3 規格，尚未實作）

`draft → proposed → approved | rejected`。觀察清單、候選配置、已核准 thesis 與實際持倉分開。Proposal 2.0 只允許未核准狀態，Decision Status 是研究建議，不是交易指令。

核准必須明確指定核准者／時間、proposal_id、確切版本／內容 hash、parent_version 與理由；沉默、模型同意與 fixture 不是核准。已核准版本不可原地修改：新證據另增 assessment；變更另建草稿，核准後新增版本與 supersession 事件，保留舊版全文。關閉 thesis 也需核准。儲存層要做版本衝突檢查與原子追加；舊提案不得覆蓋新核准版本。

實際持倉只接受經使用者明確確認的輸入／可信匯入形成新快照。AI 推薦、配置草稿或研究核准不能創造交易／持倉。

## 未來監控與風險準則

- Thesis Health 採 intact／challenged／invalidated／insufficient_data。無可靠 KPI 不產生假 0–100 分。失效是人工重評依據，不等於自動賣出。
- 同一公告／轉載以 canonical_event_id 去重，保留多來源；更正建立新版並連原事件。跨公司／產業／宏觀／組合引用同事件，不將同一衝擊加總成多個獨立損失，互斥情境不可相加。
- 重大變化包含核准 KPI／kill 門檻、治理／法規／交易狀態、曝險限額突破及關鍵監控資料失效。價格波動本身不是 thesis 失效。
- 無可驗證重大變化時，Brief 記錄覆蓋與缺口，不反覆要求核准。警示去重鍵為 thesis_version／canonical_event_id／rule_id／severity；無新證據不重發，重大更正可升級。

## 成功標準與接續順序

1. **本階段工程驗收**：120 檔以上明示 mock 母體、分批與一次跑一致、所有數量守恆、缺值／排除／失敗保留、可中斷續跑、凍結資料／方法不可悄改、不可比不排名、預算延後揭露、佇列不是研究完成、收件不核准。
2. **接續 live 驗收**：允許官方網路後，保存一次 TWSE 真實快照，人工核對主檔／欄位／日期／單位與數量；檢查缺價／負 PE／金融／新上市案例。再用少量真實候選跑完深研、三閘門與跨候選結論。測試與原始證據另存，不以 mock 取代。
3. **擴大市場與證據**：接 TPEx、ETF 官方分類與投信／指數 NAV、費用、持股、含息／風險與底層估值；MOPS 財報／營收／公告；補可重算指標及公司行動。資料授權、基準、更新 SLA、歷史窗口與預算逐項確認。
4. **Task 3**：先做 decision-recorder、thesis／portfolio／event schema、私有儲存與人工核准版本控制，再做 thesis-monitor 及其餘風險 Skills；最後接排程與 Daily Brief。通知渠道、冷卻／升級、留存／刪除與持倉匯入權限待決，不預先部署。

未來任務必須依上述產出鏈定位工作：若只增加格式、Skill 數量或漂亮敘事，卻沒有擴大可驗證覆蓋或改善決策證據，不能宣稱已完成 Investment Manager 目標。
