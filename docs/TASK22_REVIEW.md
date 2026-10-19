# Task 2.2 實作審查與驗收紀錄

## 根因與修正

原先的 Agent 01 目標為主動發掘，但 Task 2 實作只提供單次互動方法與提案驗證；沒有可執行主檔／完整母體、分批處理帳目、比較引擎或深研工作單。要求十年品質資料在每檔初篩前齊備，也使大範圍執行不切實際。這是架構／執行缺口；無法憑現有測試認定 ChatGPT 已遵守或違反特定實測流程。

本次保留 Task 2.1 決策方法，增加兩層初篩證據預算、凍結資料與政策、每檔狀態／續跑、同組排名、候選深研交接與版本化草稿收件。PROJECT 明訂完整產出鏈與 coverage，避免日後又退化成少量熱門標的介紹。沒有一次宣稱自動執行所有 Skills。

## 驗收邊界

- 合成驗收使用 100 檔虛構股票＋20 檔虛構 ETF，共六組；含停止交易、缺行情、過期行情、負 PE 與不支援 ETF 類型。17 檔一批、120 檔全數分類；離線測試確認 116 evaluated、1 excluded、3 needs_data，115 可排名，5 個待深研 packets，至少一組因預算延後。精確執行結果由生成的 ACCEPTANCE.json／REPORT.md 記錄。
- 單元／整合測試驗中斷接續、明確失敗重試、同組計分、錯誤日期／單位／小樣本降級、來源留存與 hash、mock／cutoff／版本／核准邊界及追加草稿。不是財報真實性、策略回測或 live ChatGPT 接受測試。
- 官方取數：本環境 2026-10-19 嘗試 TWSE 三個 bulk 端點、TWSE／TPEx OpenAPI 及 TPEx 日行情，皆遭網路代理 `Tunnel connection failed: 403 Forbidden`。此為當時失敗紀錄；以下更新段落記錄後續成功取數，仍不聲稱完整研究或投資建議。
- 已保存最小環境網路草稿允許 `openapi.twse.com.tw`、`www.tpex.org.tw`；草稿 requires_publish，需在環境設定檢視／儲存並發布後才生效。這不等於已取得網路。沒有停用 TLS、繞代理或用鏡像代替官方驗收。

## 與 Task 3 相容與下一步

新增 market snapshot／campaign 1.0，個別 deep-research Proposal 保持 2.0、decision component 保持 1.0；穩定 asset_id、condition_id、kpi_id、source_id 與 research_commit_sha。campaign 的 queue／drafts 不能冒充核准 thesis／PortfolioSnapshot，Task 3 仍需獨立權限、批准與私有儲存設計。

下一步先解官方網路並核對 TWSE 欄位／完整母體，再補 TPEx、MOPS、投信／指數 ETF 資料。完成真實候選深研及跨候選總結驗收後，再建 decision-recorder／Thesis Database，然後 thesis-monitor／風險與排程。不先擴充四個佔位 Skill 來假裝執行層已齊備。


## 本次整合交付

同一分支整合 Task 2.2 與 Issue #1／#2，方法包 revision 2.2.0。新增批次測試涵蓋 120 檔名單守恆、一次／分批一致、中斷接續、明確 retry、不可比／缺口降級、零深研預算、固定方法拒絕漂移、原始證據保存、條件承接、簡短摘要及未核准草稿追加。ETF／股票分組與各 profile 的數值驗證均為合成資料。

批次預設只交候選摘要；深研是待使用者選擇／已要求的工作，沒有自動 LLM。原始資料與 campaign 輸出不提交 Git。真實官方資料仍需網路開放後重新取數／欄位核對；這個 commit 不宣稱已有真實全市場研究能力。


## 官方取數狀態更新（2026-10-19，Asia/Taipei）

後續 CLI 已可取得 TWSE 三端點，原始回應有主檔 1,096 筆、行情 1,380 筆、估值 1,082 筆，行情／估值日均為 2026-10-16。初次正規化因 6 碼 TDR 而停止；修正為依官方產業別 91 分類，保留共 10 筆 TDR 為 other，股票 1,086 筆，不按長碼猜 ETF／股票，也不默默刪除母體。

原始 JSON、雜湊及失敗／正規化紀錄留於本地 artifacts，不提交個人或原始資料到 Git。本次欄位接合通過不等於財報／費用／底層估值、當前進場或整體研究結論已驗證。資料已落後研究日三個日曆日，是否可接受須依政策檢查；不冒稱即時行情。新增 4／6 碼 TDR 回歸及未識別長碼拒絕測試，保留先前 130 項完整回歸結果。
