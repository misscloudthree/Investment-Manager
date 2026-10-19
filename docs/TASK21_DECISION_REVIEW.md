# Task 2.1 根因、相容性與驗收

稽核基線：5873edbcc9d693c4d2642a3a27e8cd9ae022ce98。檢查兩個研究 Skill、Memo、Proposal Schema、資料規範、handoff、驗證器及測試。未收到第一次 ETF 研究的完整輸出／工具記錄，因此不能證明個別執行錯誤或聲稱重播了 ChatGPT 對話。

## 可證實的設計缺陷

1. company-research 的 ETF 分支偏基金盡職調查，缺獨立的「底層現在貴不貴／五年費後報酬」閘門；產品適配與投資價值混在一個結論。
2. Memo 第 6／7 節允許 ETF 只描述 pricing／structure 與文字情境，沒有強制投資結論、損益兩平、投入／分批／等待及明確重評條件。
3. Proposal 1.0 有情境文字、風險與 KPI，但沒有 investment_decision；因此未回答「現在是否值得」的 JSON 也可通過。既有測試只證明契約一致，未測決策支援品質。
4. 已有反方／kill criteria，但未要求七題逐一回答、證據不足時的 Decision Status 降級，以及 Gate 3 缺資料時的獨立狀態。

## 可能的執行未遵循（需原實測報告才能定責）

原規範已要求最新來源、日期與缺值揭露、ETF 不套公司 DCF、完整持股才評穿透、配息不等於報酬、不得用記憶行情。若實測省略／杜撰這些，屬未遵循；本任務只確定設計不足，不能據摘要斷言當時造假。價格／資料確實不足時拒絕下推薦是正確行為，缺陷是未說明決定性缺口及補證方式，不能為了「有答案」強推投資。

## 修正與相容性

- canonical 方法仍只在兩個 Skill，增加三閘門、ETF 證據／報酬分解與七題反方；handoff／Memo 只規定載入與呈現。
- Proposal 2.0 是明示的 breaking change：新增必要 investment_decision（其 component contract_version=1.0）。唯一 canonical proposal 路徑不變；歷史 1.0 以原 Git commit 的 Schema 驗證，不能用新版本靜默判為通過或覆寫舊資料。
- 舊研究工作表仍相容；convert 產生新 2.0 提案時初始化 Insufficient Evidence、空假設報酬與 Gate 3 Not Assessed，不把舊產品介紹轉成推薦。schema_version、proposal_id、asset_id、research_commit_sha 與原 KPI／trigger IDs 保留用途。
- Decision Status 與 proposal_status／人工 approval 分開；未來 Task 3 Database 追加存整份不可變提案、三閘門、假設與 source IDs，按 condition_id→linked_kpi_ids 建重評規則。沒有實際 Task 3 Database 可做遷移測試，本次只驗契約相容邊界，不宣稱已整合 DB。
- 新 recommendation 不修改已批准 thesis／持倉。Insufficient Evidence 的證據缺口不等於論點失效；Gate 3 Not Assessed 也不是組合風險事件。補證後新增研究版本，再由人工核准。

## Mock 驗收範圍

測試固定假設資金 TWD 1,000,000、五年、缺持倉／風險／用款資料，候選 0050／00646／00713。Mock 產品證據可令 Gate 1 通過，但行情、底層估值與前瞻輸入缺失時 Gate 2 必須 Insufficient Evidence；Gate 3 Not Assessed；最終 Insufficient Evidence。這證明產品合格不會被偷換成可以投資，不是真實三檔 ETF 評等。

分別測試：必要資料完整的合成推薦、分批、等待與不投資、缺／衝突降級、假推薦被拒、未設定個人資料不得 Suitable、錯誤數值情境／雙扣成本被拒、break-even 代回、歷史／追蹤統計、反方未解則降級、日期／版本／依賴回歸。輸出為合成 Decision Proposals 與比較報告；沒有實際執行 ChatGPT live 研究，無當前行情或可信市場預測。

## 尚待真實驗收

取得三檔官方商品與指數資料、同日或可對齊價／NAV、實際費用、含息歷史／基準、底層估值與盈利、匯率與可比較替代資料，以及使用者持倉、風險承受與用款需求。逐欄核對來源與調整，評估輸入合理性，再以新版 ChatGPT 方法重跑並人工審查。正式 3–5 年投資建議、API／排程及核准持久化仍未完成。
