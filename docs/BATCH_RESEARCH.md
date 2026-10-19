# Task 2.2 批次研究操作與交換契約

本文件定義執行與交接；分析方法以兩份 canonical Skills 為準。Python 3.12，先安裝 `requirements-dev.txt`。這是手動批次初篩，不是自動完成財報研究的 AI 服務。

## 可運行的入口

先提交已審閱方法及 manifest，使用同一 checkout：

```sh
# 官方最新 TWSE 上市公司主檔＋當日全量行情／PE/PB，非逐檔爬取
python -m src.batch_research capture-twse --output-dir data/snapshots/twse-capture-001
# 不指定 policy 時以 snapshot captured_at 為 cutoff，採預設 profile／預算
python -m src.batch_research init --snapshot data/snapshots/twse-capture-001/snapshot.json --run-dir data/campaigns/research-001
python -m src.batch_research process --run-dir data/campaigns/research-001 --max-items 100
# 重複 process 直到 coverage.pending=0；中斷後用相同命令接續
python -m src.batch_research export --run-dir data/campaigns/research-001
# failed 只在明確指定時重試；缺資料應補新 snapshot／另開 campaign
python -m src.batch_research process --run-dir data/campaigns/research-001 --max-items 100 --retry-failed
```

官方網路遭阻擋時退出非零，保留 fetch_attempt.json；不改用 mock、舊資料或模型數字冒充最新資料。三端點缺一即不產生成功 snapshot。有限 timeout、暫時錯誤最多兩次嘗試；403 不重試，不停用 TLS／代理。初始欄位映射只通過合成來源測試，live 須另驗。

自訂政策用 `--policy config/batch-policy.example.json`，先把例子 as_of 改成該快照已擷取之後的明確截止；不能拿歷史例子直接套今日快照。截止含 timezone、行情日以台北日期計，max_quote_age_days 是日曆日；預設 7 天只供資料可用性，不是每個策略的理想時效。min_turnover_twd 是當日金額，不是 20 日均量；不提供個人流動性適合度。深研名額 0 可只做初篩，不表示完成研究。

## 資料契約

- `schemas/market-snapshot.schema.json` 1.0：snapshot_id 為移除自身欄位後、UTF-8／sorted keys／compact JSON 的 SHA-256；有 captured_at、data_mode、scope、sources 與 instruments。每檔 identity 為 market:ticker，代碼保留字串；類型由主檔／匯入證據決定，不能猜 00 開頭就是 ETF。
- scope 的 full 是對 **label 明確界定的官方母體** 完整，不等於全台灣；user_declared 只能 sample。mock 身分與數值必須標示，不能修改 data_mode 偽裝真實資料。這些標籤與 hash 不提供來源認證，仍需核對原文。
- source 必須有 locator、provider、retrieved_at、data_as_of（可 null）、published_at（未知 null）。官方 capture 保存 raw_file／raw_sha256；init 驗證並複製至 campaign，拒絕缺檔／路徑穿越／hash 不符。匯入文件無 raw 時須另保留可查原文；不能只憑填入 source_id 稱 verified。
- metric 為 value（有限數字／null）、unit、as_of（此數字在比較日已公開可得的狀態日）、source_id。財報年度／季別放 period，計算公式放 formula，TD/TE／費用比較窗口放 window；不可把報告期末當作公告已知日期。所有參與同組計分的資料必須是組內最新 quote 日期的可比快照，日期／單位不符不評分；不會自動補價或對舊資料 forward-fill。
- close 單位 TWD/unit、turnover_twd 為 TWD、pe/pb/ev_ebitda 為 multiple，其餘 profile 因子為小數 ratio（例如 5%=0.05）。同組相同方法／期間／幣別／稅務／調整口徑由匯入者核對，單位檢查不會自動驗證經濟可比性。PE/PB 非正值不可當作便宜；缺失不是零分。
- `schemas/research-campaign.input.schema.json` 1.0：事先固定 profiles、截止、行情容許日數、成交下限、minimum_peers、每組 shortlist 與 deep_research_limit。方法細則只在 screener Skill。
- `schemas/research-campaign.output.schema.json` 1.0：coverage、逐檔狀態、同組 ranking／peer_evidence、研究 queue／預算延後、來源與方法 SHA。這不是舊 screener 五因子工作表；基本榜不可填到那份 composite 欄位冒充完整分數。個別深研仍用唯一 Thesis Proposal 2.0，不修改 Task 3 核准契約。

## 狀態、預算與重跑

SQLite 僅為本地 ResearchRun 儲存，非 Thesis Database。每筆原子轉移 pending → evaluated／excluded／needs_data／failed；所有 terminal 狀態含理由／缺口／來源或錯誤。evaluated 僅代表有資格比較，不等於可排名；因子不全仍 score/rank=null。pending>0 不出完整排名或 queue。

研究身份固定 snapshot＋policy＋methodology（已提交 SHA、manifest hash、兩個 Skill revision/hash、引擎 hash）。母體／資料／政策／方法改變須另開 campaign；可用原版程式續跑原 campaign。engine 不同拒絕續跑。重複 process 不重做已完成項；重複 submit 相同內容返回既有版本，改內容追加版本，不覆寫 SQLite 草稿。

完整分類後各組選 shortlist，再按 profile／group 排序輪流分配有限深研名額。這是透明、可重現的預算分配，不能把字母較前組別的名額說成投資較好；REPORT／JSON 明列 deferred_groups／deferred_ranked_assets。需要改預算時另開 campaign（同 snapshot 可重用）。目前為單使用者順序 CLI，不支援多 worker 或服務併發協調。

## ChatGPT 深研與回收

產出 `REPORT.md`、`campaign.json`、`ledger.csv`、`CHATGPT_RESEARCH_BRIEF.md` 和 `queue/*.json`。初篩 REPORT 不是完整投資總結，queue packet 不是完成的 Memo。把這些與同 SHA 方法 bundle 交給 ChatGPT；方法載入後逐檔按 company-research 補官方長期／前瞻／ETF 證據並比較替代，交 14 節 Memo 與 Proposal。

```sh
python -m src.batch_research submit --run-dir data/campaigns/research-001 --asset-id TWSE:2330 --proposal /private/path/proposal.json --memo /private/path/memo.md
```

2330 僅為指令格式，必須在該 campaign 完整 queue 內才收件。收件驗資產、mock/real、deep_research、相同 cutoff、固定 SHA／manifest、Proposal 契約及 Memo 14 節；相同 Memo／Proposal 內容不重複新增，修改追加 v2 等。格式通過不代表內容有真實研究品質；不比對所有 Markdown 敘述與 JSON，因此研究者仍須逐項核對一致性。若要用晚於 campaign 截止的資料，重開 campaign，不偷偷延長 cutoff。

收齊 queue 草稿後 status=ready_for_synthesis_not_approved；研究者還須交跨候選支持／反對、三閘門、現在／分批／等待條件、同目標替代與重大缺口。缺個人資料不阻止資產研究，但 Gate 3 Not Assessed／個人決策 Insufficient Evidence。所有草稿保留 version，沒有批准／持倉變動。

## 離線驗收與 live 驗收分開

```sh
python -m unittest discover -s tests -v
# 方法提交後執行；120 檔虛構標的，17 檔一批，自動接續至分類完成
python -m examples.batch_research_acceptance --output-dir /tmp/task22-mock
```

這只驗批次工程／契約，**未執行 ChatGPT 深研、真實全市場比較或投資建議**。live 另需官方網路、實際欄位映射驗證、數量核對及人工來源／計算驗收。TWSE 基礎 adapter 不能產生 ETF 深研所需的 NAV／總費用／含息歷史／底層估值。


## 與條件承接／漸進揭露整合

`init --context /private/path/research-context.json` 可沿用五項已知條件／來源／時間；不指定時明示 provisional_screening，不假裝得知持有期、風險或報酬目標。awaiting_conditions 的輸入會拒絕啟動，需補條件或明示可暫定探索。對話的自然語言限制須先由研究者核對／正規化到母體，CLI 不解析「僅元大」等文字，不自稱已自動執行所有個人限制。

context 與 snapshot／policy／方法一同凍結並傳入 campaign、queue 和 Proposal。收件保留原 conditions，顯示深度偏好可從 snapshot 轉 deep_dive；改投資條件或截止須新 campaign。ETF vehicle 只接受明示被動非槓桿且 underlying_asset_class=equity；不能因同樣被動就把債券 ETF 加入股票型比較。

分類完成且有候選時另產生 `DECISION_SNAPSHOT.md`／`decision-snapshot.json`，預設以簡短候選摘要供使用者選擇深研，完整 REPORT／ledger 為可查附錄。原始合理價及前瞻證據未齊，摘要維持 null／Insufficient Evidence，不把排名變推薦。所有候選 work packets 都是待查工作單；沒有自動呼叫 LLM。已明確要求深研則沿用條件直接展開，不再詢問詳細版。

研究預算為零時 status=screening_complete_no_deep_budget，保留完整比較，不誤稱無可比標的。raw 檔限 raw/，初始化及續跑核對雜湊，不得覆寫 SQLite 或越出 campaign 目錄。初篩重試後會清除已過時的 generated queue／摘要，避免把舊候選當最新名單。

續跑／匯出同時核對已凍結的 manifest hash 與全部材料 hash；即使批次引擎檔本身沒變，換了 Skill、Schema 或共用驗證程式也須回到原版本或建立新 campaign，不能混用新方法產生舊版結果。
