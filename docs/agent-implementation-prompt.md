# 第一個可貼給 Codex 的開發任務

請把這個投資研究 MVP 擴充成可信且可審計的台股與基金資料工作流。

先不要串接券商、不要自動下單、不要產生 Buy/Sell 指令。

工作順序：
1. 檢查 README、AGENTS.md、所有 `.agents/skills/*/SKILL.md`、`docs/data-contract.md`。
2. 規劃 data provider interface：TWSE 上市、TPEx 上櫃、FinMind 整合、基金官方 NAV/持股、宏觀發布日曆。
3. 先實作 TWSE 日資料驗證 connector：檢查來源、發布日期、交易日、價差與分割/除權口徑；用固定 fixture 寫 unit tests，遇缺失 fail closed。
4. 增加每資產 Thesis JSON schema、Approval log（草稿不可寫入 approved 版本）。
5. 加 `macro-industry-risk` event mapper（事件 -> 類股 -> KPI），先用有日期、來源的測試事件驗證。
6. 用獨立 test cases 驗證：過期資料、基金 NAV 滯後、ETF 重疊、持股=0、來源矛盾、定時失敗、錯誤新聞、重複事件。
7. 完成報告樣板（日報 + 危機警示）後，最後才接入 LLM API + 推播。

每次提交前列出已實現/未實現、資料源與授權問題、測試結果；不要聲稱 demo 已是 live 投資風險模型。
