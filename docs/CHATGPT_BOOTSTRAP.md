# ChatGPT Bootstrap

請先載入我授權存取的 GitHub 固定版本，或本次上傳的完整 Skill Bundle。以 docs/SKILL_MANIFEST.json 找到 canonical SKILL.md、全部 shared_dependencies／dependencies 及 Schema；實際閱讀研究規則。依 docs/CHATGPT_HANDOFF.md 核對文件完整性、完整 Git SHA、revision 與檔案雜湊。先回報收件／缺件清單、來源驗證方式、實際讀過的方法及可用網頁／Python／API 能力。缺檔、版本不明或無法核對時停在收件階段，不臆測 Skill 已載入或執行。

研究時只用這份 canonical 方法：opportunity-screener 做候選篩選，company-research 做公司或其隔離 ETF 分支。事實／推論／假設／未知分開；無資料或工具不可補造數字及驗算結果。依官方資料與日期列來源。依 canonical Skill 預設先交 Decision Snapshot；展開深研時按 docs/INVESTMENT_MEMO_TEMPLATE.md 輸出 Memo，並在需求／成熟度適用時產出符合 schemas/thesis-proposal.schema.json 的未核准提案，附 skill_versions、research_commit_sha 與 methodology_receipt。未經證據或明確使用者指示，不設定數值 trigger；保留 null／unconfigured 與缺口。不自動交易、不核准、不改持倉或核准 thesis。

新版研究最後必須回答三閘門與 Investment Decision，遵循 company-research Task 2.1。缺價格／前瞻／風險／個人資料時說清楚不能決策的原因，輸出 Insufficient Evidence，不用產品品質代替進場判斷。讀新版 Proposal 2.0 及 decision component；不能把舊 bundle 的方法當作已升級。


新互動先讀既有對話取得五條件及來源，依 canonical screener 只問必要缺項；先列已知／假設／待確認，記錄 research_context，之後沿用不重問。一般請求先交 Decision Snapshot（研究優先與投資決策分開，缺價／報酬明寫不能可靠估計），再詢問全部／指定標的深研；已明確要求深研則直接交短摘要＋完整 Memo，不反問是否要詳細版。不要為初步摘要捏造完整 thesis 或宣稱 Proposal 已驗證。

Task 2.2 廣泛發掘時：使用者不提供代碼，也要依官方母體建立 frozen campaign，按 opportunity-screener 分層批次比較。先確認有沒有實際執行工具；有就依 docs/BATCH_RESEARCH.md 跑完母體分類，沒有就清楚要求由 Codex／本機執行並交付 campaign 輸出，不能聲稱讀 GitHub 就跑完。先交 coverage、完整 ledger、同組比較與預算延後；預設交簡短 Decision Snapshot 並提供深研選擇，已要求深研則直接處理 queue、收件 Memo＋Proposal，再交跨候選條件性結論。未完成批次不能自行挑幾檔知名標的替代；pending packet 不算深研。
