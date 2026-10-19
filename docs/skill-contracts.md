# 兩個優先 Skill 的交換契約

版本 1.0，JSON Schema Draft 2020-12。`schemas/` 是機器可讀結構；Skill 的方法步驟與共用資料規範提供語義約束。Schema 通過不表示資料真實、估值正確、使用者已核准或服務可執行。正式 thesis／持倉／核准事件的儲存契約將在下一階段建立。

## 輸入

共用：`schema_version`、`request_id`、含時區 `as_of`、`horizon_months`、`base_currency`、`source_inputs`（官方 URL／本地快照／使用者文件定位，不包含任何金鑰或帳戶資訊）。

| Skill | Schema | 其他必要欄位 |
|---|---|---|
| opportunity-screener | `schemas/opportunity-screener.input.schema.json` | universe（mode、instruments、selector、full/sample）、benchmark、filters、stock_weights |
| company-research | `schemas/company-research.input.schema.json` | instrument、research_question、peer_instruments、approved_thesis_ref、portfolio_snapshot_ref；後兩個沒提供時用 null |

instrument 含字串 ticker、name、TWSE/TPEx、stock/etf、三碼 currency。`0050` 前導零不可遺失；金融業仍是 stock，由研究分類決定指標。Schema 不驗證代碼真實存在，必須查官方主檔。

輸入缺可合理推定的偏好時，Skill 先列明假設／預設並正規化為完整輸入，不默認使用者風險預算、實際持倉或核准狀態。只有無法推定且阻礙研究的資訊才需要提問。

篩選預設 stock_weights：valuation=0.20、quality=0.25、momentum=0.20、sentiment=0.15、growth=0.20；若使用者另訂，需記錄，總和必須為 1。ETF 不使用此組權重。

## 輸出

共用 `meta`（run_id、generated_at、as_of、Asia/Taipei、confidence、complete/partial/blocked、approval_status 固定 draft、limitations、sources、data_gaps）。complete 表示這次研究流程的證據檢查完成，不表示 thesis 已核准或軟體上線。

來源欄位：source_id、provider、locator、data_period、published_at、retrieved_at、retrieval、confidence。可用日期的官方文件若無確切時刻，須按 adapter 的明示保守政策處理並列限制，不能捏造精確公告時間用於盤中／歷史可得性判斷。

數值 metric：name、value（number 或 null）、unit、currency（不涉及金額時 null）、period、classification、quality、source_ids、formula。已驗證事實必須有數值與來源；未知必須 null，不能用 0。單位元／千元／億元、%／小數須明示。JSON number 是交換表示，未來計算模組以 Decimal／足夠精度處理，再按輸出規則量化。

claim 是帶來源的文字主張，標為 verified_fact/inference/assumption/unknown，附 counter_evidence。kill criterion 包含論點 ID、基準、門檻、窗口、資料源及重評動作。

### 篩選輸出

`schemas/opportunity-screener.output.schema.json`：

- universe_summary：母體類型、full/sample、declared/evaluated/excluded/missing 數及來源。evaluated 定義為成功產生可比較結果的數量，excluded 為依政策排除，missing 為未完成評估；三者互斥，總和 = declared_count。
- stock_candidates：個股、比較組、ranked/insufficient_data/excluded、rank、五維分數、composite、coverage、metrics、理由／旗標／來源／信心。只有 ranked 可有排名與總分；缺資料不打零分。
- etf_candidates：ETF 策略、七項 checks、fit/review/insufficient_data/purpose_mismatch、metrics、理由、風險與 holdings_coverage；不接受公司五維分數。
- follow_up：下一個研究標的、理由、最強反方、失效條件與下次檢查日。排名只能比較同組，不把不同類 ETF 與股票混在一起。

### 研究輸出

`schemas/company-research.output.schema.json`：

- instrument、path=company/etf、verdict、summary、information_richness、thesis_pillars、risks、kill_criteria、next_checks。
- company 路徑要求 company_analysis：商業模式、財務快照、品質、護城河／治理、五向檢驗、估值。估值若 assessed 必須 bear/base/bull 各一、可計算的公允價、計算紀錄與敏感性；不適用／缺資料時 method=not_assessed，scenarios=[] 並列限制。
- etf 路徑要求 etf_analysis：基金卡、策略／指數、七項 checks、曝險／費用追蹤指標、配息、結構、同類比較、重疊狀態／持股覆蓋。禁止 company_analysis；ETF 不應收到公司 DCF。
- complete 研究要求 3–5 個論點、來源、至少一個失效條件及後續檢查；partial/blocked 不強迫生出缺乏證據的論點。

## 執行前後的語義檢查（目前尚無 runtime validator）

JSON Schema 能檢查型別、必要欄位、取值範圍、null／分數與公司／ETF 分支，**不能單獨保證**：

1. source_id／claim_id 唯一及引用存在；每個 kill 指向現有支柱；一手來源與獨立交叉驗證的可信度。
2. 公告／資料／擷取時間與 as_of 的先後、交易日、文件版本、資料最新性；禁止歷史研究前視。
3. 權重和為 1、母體計數守恆、同組排名無跳躍、五維分數算式、每維至少 75% 覆蓋與有效同業至少五家；總覆蓋率高不能掩蓋單一維度缺失。
4. 單位／幣別、累計差分、TTM、股數、公司行動、DCF／TE／折溢價的算式與精度；估值有效性、情境輸入合理性。
5. ETF 實際商品結構與使用者用途匹配；holdings_coverage<1 不得稱完整重疊；未提供 portfolio_snapshot_ref 時 overlap_status 必須 not_assessed。
6. 事實、推論與假設的真實分類、同事件不重複計風險、研究結論與資料品質一致；關鍵缺值時必須 partial/blocked 且列 gaps。
7. 人工核准、不可變持倉與 thesis 版本須由未來權限／儲存層執行，不能靠 LLM 或 draft 欄位充當安全控制。

目前人工依此清單審閱；下一階段以 Python 可測試實作，未通過就不能稱真實投資研究已驗證。

## 樣本與檢查

`tests/fixtures/` 四份輸入／輸出全是合成、部分資料不足的樣本，使用虛構代碼；不代表真實行情、持倉、核准或投資建議。`python -m unittest discover -s tests -v` 驗證結構、負向案例與文件／固定版來源參照。當前沒有 adapter／財務計算／端到端／排程測試可執行。
