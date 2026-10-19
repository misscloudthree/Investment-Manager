# ChatGPT 研究交接

GitHub 的 `.agents/skills/*/SKILL.md` 是方法唯一來源；本文件只定義載入／驗證協定，不重寫方法。ChatGPT 不會自動取得 Codex Skills、私人 GitHub 權限、API、Python 或排程能力。

## 研究開始前的收件與能力檢查

1. 選定 `company-research`（單一股票／ETF 深度研究）或 `opportunity-screener`（候選清單）。ETF 保留 `company-research` 的隔離分支，沒有第三份獨立方法文件。
2. 取得 `docs/SKILL_MANIFEST.json`。以 canonical_path 與 shared_dependencies／dependencies 收齊全部文件；目前研究 bundle 同時帶兩個 Skill，因公司研究依賴篩選的 ETF 檢查，不能只上傳一個 SKILL.md。
3. 核對完整 Git commit、Skill revision、每份原始位元組 SHA-256、manifest hash、所需 Schema 與其 `$ref` 閉包。缺文件、截斷、版本不明或 hash 不符就停止「正式研究」並列出缺口，不用模型記憶補方法。
4. 明列已讀方法與尚缺文件、來源驗證方式、可用工具（網頁、Python、資料 API）、計算狀態。文件已收到／hash 相符不代表 Skill 已執行；聲稱讀過須實際閱讀，聲稱驗算須保留計算紀錄。
5. 研究只採截止時間前可驗證資料。無瀏覽／API 可請使用者提供有日期來源的財報或 CSV；無 Python 不假稱已跑計算，標示未驗算與限制。

## Mode A — 授權 GitHub 存取

由現有 connector、可用瀏覽工具或本地 checkout 讀取被授權的 Repository。先解析實際 SHA，再在該固定 SHA 讀 manifest、Skill 及依賴；不要在研究中混用浮動 main。私有存取失敗不代表有 token 可取用，也不要要求把 API key 或 GitHub token 貼到對話。

本地工具可用時：

```sh
python src/research_handoff.py check-materials
```

此命令只核對目前工作區檔案，不聲稱版本已提交。正式 bundle／proposal 驗證會使用 Git 中確實存在的提交，方法檔案未提交不能打包。GitHub 網頁或 connector 若不能完整讀取檔案與確認 revision，改用 Mode B。

## Mode B — 可攜 Skill Bundle

在受信任的 checkout、安裝 requirements-dev.txt 後，將審閱完的 Task 2 方法與清單提交 Git，再執行：

```sh
python src/research_handoff.py bundle --output /tmp/investment-research-skills.zip
python src/research_handoff.py verify-bundle /tmp/investment-research-skills.zip
```

bundle 從 HEAD 的已提交位元組建立，不包含 `.git`、API keys、私人資料、持倉或批准紀錄。包含 manifest、兩個原始 Skill、共用規格、資料規則、Schema 閉包、來源／授權、Memo 模板、bootstrap、交接文件和驗證工具。`BUNDLE_METADATA.json` 記錄 research_commit_sha、全部檔案雜湊與來源 Repository。

把 ZIP 上傳 ChatGPT。若 ChatGPT 不能讀 ZIP，使用本機 ZIP 工具解開自己產生的包，再上傳清單中的原始檔；不能只貼摘要／重新排版 Skill。檔案很多可分批，未收齊前只做收件檢查，不開始研究。

verify-bundle 只在記憶體讀取 archive，不自動解壓或執行其中程式；拒絕缺檔、重複、路徑穿越、symlink、額外檔案與過大 archive。SHA-256 可檢查傳輸完整性，但不是簽章：惡意者可同時改文件與 metadata。SHA 標籤相同也不是 GitHub 作者身分的密碼學證明。請對照受信任 checkout 的 commit／manifest／hash 或透過授權 GitHub 確認，才將 origin_authentication 設為 trusted_repository／user_compared_commit；否則保持 not_verified，proposal 不能 ready_for_review。

`--expected-commit <完整SHA>` 可以檢查包中的 commit 標籤是否符合預期，仍不提供遠端認證。ChatGPT 無法計算雜湊時，請使用者執行本地驗證並提供輸出，記錄驗證者與限制；不要宣稱模型自行驗證，也不要憑 metadata 自述判定安全。

## Bootstrap 與交付

先貼 [CHATGPT_BOOTSTRAP.md](CHATGPT_BOOTSTRAP.md)。執行自然語言研究步驟；Python、網路查詢及 API 是另行檢查的能力，不是讀到 SKILL.md 就會發生的動作。

完成深度研究交付：

- Investment Memo：套用 [INVESTMENT_MEMO_TEMPLATE.md](INVESTMENT_MEMO_TEMPLATE.md)，按資產路徑解釋，不複製／另創方法。
- Thesis Proposal JSON：唯一正式提案契約 `schemas/thesis-proposal.schema.json`；proposal_status 僅 draft／needs_information／ready_for_review，絕無 approved。所有人工核准、永久保存及持倉異動屬 Task 3。

篩選先交 Candidate List／理由／來源／Research Priority／缺口，以既有 screener JSON 作中間資料；若為單一候選產生 proposal，research_stage=screening 且不得 ready_for_review，不把候選排名當完整 thesis。

舊 `company-research.output.schema.json` 仍是研究工作表／中間契約，不是另一份提案 Schema。已有這種輸出可透過 convert 保留原始 analysis，建立 needs_information 提案；不推測 KPI 數字、approval 或 user intent。

## 如何測試第一檔股票

1. 在 GitHub 方法已提交後產生 bundle，上傳 ChatGPT；貼 bootstrap，請它先回報收件清單、版本、SHA、工具可用性，確認沒有缺依賴。
2. 再貼：

   「請使用已驗證版本的 company-research，研究 TWSE:2330（台積電），投資期間三年，截止日為本次研究日。先以官方主檔確認身分。依可用官方財報／公告研究；缺資料列未知，不編估值或 KPI 門檻。請交付 Memo 與 draft Thesis Proposal JSON，記錄來源日期、方法 revision 與 research_commit_sha，不核准、不交易。」

   此處僅示範操作，不代表已取得 2330 的最新資料或投資建議。無瀏覽能力就改上傳 MOPS 年季報及官方日期行情；若缺關鍵資料，needs_information 是正確結果。
3. 下載 JSON 到私有位置，在同一版本的 checkout 驗證，或指定原 bundle：

```sh
python src/research_handoff.py validate /private/path/proposal.json --bundle /tmp/investment-research-skills.zip
```

   驗證成功只表示 Schema、版本、檔案清單與部分引用／時間規則一致；不能證明資料數字正確或 thesis 有效，仍須人工核對官方原文、計算與門檻理由。首次 live acceptance 必須另存真實來源與檢查結果，不用 mock 通過冒充。

## 可重現的離線範例

以下使用 Task 1 的「合成、資料不足 ETF」工作表，不連市場 API：

```sh
python src/research_handoff.py convert tests/fixtures/company-research.output.json --data-mode mock --memo-path synthetic-memo.md --output /tmp/synthetic-proposal.json
python src/research_handoff.py validate /tmp/synthetic-proposal.json
```

convert 不會自動寫 Memo、填 KPI、決定數值門檻、提升 ready_for_review 或保存核准紀錄；它是工作表到提案草稿的保守映射。ChatGPT 也可直接按提案 Schema 產生 JSON，然後用同一驗證工具檢查。


## 維護 manifest

變更 canonical Skill 或任何必要依賴後，先審閱差異並遞增方法包 revision（X.Y.Z），再執行 `python src/research_handoff.py refresh-manifest --revision <新版本>` 與測試。此命令只刷新既有依賴清單的 hash／revision，不會自行發現新依賴；新增引用檔案仍須先更新清單並確認 Schema 閉包。不要為了讓不可信檔案「通過」而盲目刷新。提交所有必要檔案後才能 bundle，避免把前一個 HEAD 冒稱成當前修改。


## Task 2.1 — 決策品質交接與驗收

使用 manifest 的目前方法（Task 2.2 為 2.2.0，含 Task 2.1 決策規範）及 Proposal Schema 2.0；載入新 `schemas/investment-decision.schema.json` 與 `src/investment_decision.py`，不要將 Task 2.0 bundle 與新版 Schema 混用。舊 commit 的 1.0 提案保持歷史版本；新工作表 convert 只補未評估決策，不轉成推薦。

完整深研先依 company-research 的三閘門與七題反方，最後交付 Memo 第 14 節與 investment_decision。Asset Quality Pass 不代表 Entry Attractive，Not Assessed 不能當 Suitable。資料不夠時輸出 Insufficient Evidence、null 報酬與決定性補證清單；有資料才談「等待哪些市場條件」，不要以 Wait for Conditions 隱藏缺資料。

Decision Status（五種研究建議）與 proposal_status（未核准工作流程）分開；即使 Invest Now 也不是批准或下單。Gate 3 缺持倉／風險／用款需求必須 Not Assessed，最終個人建議為 Insufficient Evidence。財務模型只可在有來源／理由的輸入下執行；缺 Python 就不能宣稱已驗算或提供精準數字。

可把首次操作提示改為：「請研究現在投入假設 TWD 100 萬、持有五年的 0050／00646／00713。我尚未提供完整持倉、風險承受及用款資料。先比研究問題，再分開完成三道閘門；不要自動分配資金。最後附 Investment Decision、逐項可重算三情境及反方審查；資料不足明示 null／Insufficient Evidence 與官方補證方式，不編現在行情或合理買價。」

離線驗收（只在完整 checkout 或可讀完整 bundle 的環境）：

```sh
python -m examples.etf_decision_acceptance --output-dir /tmp/task21-mock
# 如無 Git checkout，可加 --bundle <已驗證新版 bundle.zip>
python src/research_handoff.py validate /tmp/task21-mock/TWSE-0050.json
```

mock 程式只建立／驗證合成決策契約，不執行 Skill、ChatGPT 或市場研究。三檔皆應 Gate 1 Pass（僅合成資料）、Gate 2 Insufficient Evidence、Gate 3 Not Assessed，最終 Insufficient Evidence。完整真實接受測試仍須逐欄取官方來源、核算與人工評估假設；詳見 TASK21_DECISION_REVIEW.md。


## Task 2.2 — 廣泛發掘的交接與使用提示

使用者不給代碼的探索請先跑 campaign；完整指令與輸出契約見 [BATCH_RESEARCH.md](BATCH_RESEARCH.md)。Mode A／B 是讀方法的方式，不是執行服務。Python／網路工具不足時交代缺口，由 Codex／受信任本機取數與分批處理，再把同版本 bundle 與整份 run 輸出交給 ChatGPT。公開 GitHub 不放 run 私人資料。

提示範例：「以五年持有為研究目標，從已驗證的台灣市場母體主動找候選。先說明能取得的交易所／商品範圍，不要求我先給代碼。使用固定版本 Task 2.2 方法：保存母體、分批續跑到全數分類、交 coverage／ledger／組內比較／預算延後，再深研候選並給有證據的條件性結論。我未提供完整持倉／風險資料，不自行分配資金。不能執行批次或取官方資料時列阻礙，不用幾檔熱門標的代替。」

接收 REPORT.md／campaign.json／ledger.csv／queue packets／CHATGPT_RESEARCH_BRIEF.md 後，核對 cutoff、data_mode、method commit 與 processing_complete。按 canonical company-research 逐檔補證，交每檔 Memo＋Proposal；用 batch_research submit 保留版本與驗證結果。最後綜合研究結果及未完成範圍，不把 ranking 或 packet 當結論。

新增 batch／snapshot schema 1.0 與 Proposal 2.0 各有用途，沒有新核准狀態。建 bundle 前刷新 manifest 2.2.0；bundle 包含執行工具與可攜 mock 範例，但不會在上傳時自動執行。人工資料／API 的實際能力及真實數值仍需逐次驗證。
