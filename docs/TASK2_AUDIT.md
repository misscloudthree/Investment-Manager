# Task 2 稽核與決策紀錄

基線：`7564b4eb0e4b5dcabd92935de6f4e846a9ae3b4a`。已讀 AGENTS、PROJECT、README、兩個研究 Skill、四個佔位 Skill、既有 Schema／測試、共用資料／來源與授權文件，以及離線 src/run.py。工作區起始乾淨。

## 差距與保留

- Task 1 已有具體台股／ETF 方法與工作表 Schema；保留方法與檔案，補產業鏈／競爭比較、投資安全邊際、KPI 設計與 ChatGPT 交接。既有 Schema 不改名、不偽稱它是 approved thesis。
- 合併時遠端已加入 src/run.py 與四個離線示範測試、demo JSON；其 alert_priority_demo_0_100 不是實際組合風險。保留示範，不在 Task 2 延伸監控／排程。Task 1 稽核是當時快照，非現況清單。
- 缺少方法 manifest、版本收據、ChatGPT 存取／上傳流程、Memo 模板、獨立提案契約與可執行的本地輸出驗證；Task 2 補上。
- 仍不實作資料 API、金融計算引擎、批准後端、持倉變動或正式 GitHub Actions。已存在 demo 不代表這些能力已具備。

## ETF 架構決定

維持 company-research 中隔離 ETF 工作流，opportunity-screener 做輕量 ETF 篩選；共用 canonical 方法不另建第七個 Skill。原因是 Task 1 已有分支與互斥 Schema，單一公司／基金入口更易維護與交接。manifest 將兩個 Skill 都列入完整 research bundle，避免公司研究引用 ETF 七項檢查卻漏載來源。Memo 只是輸出模板，不另養方法副本。未來若 ETF 分支依賴／版本獨立到足夠大，再透過正式設計變更抽出。

## 來源與版本決定

沿用 Task 1 三個固定上游 commit，不追逐浮動 main。新增檢查 InvestSkill industry-map／competitor-analysis，並依 stock-eval 補安全邊際定義。AI Berkshire 的 moat-analysis、valuation、reverse-thinking 是 investment-research 的段落概念；所檢查版本沒有對應獨立 SKILL.md，不捏造同名路徑。XVARY 仍僅用公開方法，不聲稱重現專有權重。見 skill-provenance 與 MIT notices；沒有執行上游工具。

## Task 2 驗證範圍

契約測試與 package integration 全使用清楚標記的合成資料；檢查 stock／ETF、缺值／衝突、來源／KPI 引用、錯誤提案、缺依賴、未知版本、bundle 完整性及離線轉換。測試結果在交付時報告。真實 ChatGPT 首檔研究、官方資料準確性、財務計算與研究有效性是另外的 live acceptance，不能以 mock 通過宣稱完成。


## 本次驗證記錄

完整測試命令為 `python -m unittest discover -s tests -v`（Python 3.12、requirements-dev.txt 的 venv），同時檢查既有四個 demo 測試與 Task 1 契約。新增測試將必要 canonical 檔案複製進暫存 Git Repository 並建立測試提交，驗證真正的 commit-pinned bundle，而不是塞入虛構 SHA。

交付另外執行本 Repository 已提交版本的 check-materials、bundle、verify-bundle，以及 stock／ETF 合成工作表的 convert → validate CLI 往返。所有輸出仍為 mock／needs_information；未進行實際 ChatGPT 對話或 live 金融資料測試。完整測試總數與結果由交付訊息報告。
