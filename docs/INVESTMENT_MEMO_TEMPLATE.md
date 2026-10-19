# Investment Memo — <名稱／asset_id>

模板版本：2.1；此文件只規定呈現與索引，分析步驟以 manifest 指定的 SKILL.md 為準。本模板用於已要求／已展開的深研，每節保留；一般探索先按 canonical Skill 交 Decision Snapshot，再詢問是否展開。明確要求深研者直接交短摘要＋本模板，不再確認。資料不足或不適用時說明理由。公開／匿名文件才進 Git，私人資料另存指定受控位置。

## 1. Executive Summary

開頭放精簡 Decision Snapshot：商品、決策／研究優先度、2–3 核心原因（含反方）與下一步、合理進場價、期限總報酬、1–3 風險／翻轉因素、催化劑窗口、替代與取捨。估值／報酬無可靠資料時明寫「未能可靠估計／尚無可信估計」並列缺口，數值不亂填；方法見 canonical Skill。

沿用 research_context 列已知條件／假設／仍需確認，包含商品範圍、持有期、進場窗口、累積報酬目標／期限、定性風險／未知最大虧損、對話來源與記錄時間，不重問已知條件。

研究問題、資產類型、研究截止日／時間（Asia/Taipei）、結論與 Research Priority、信心及最重要缺口。明示 draft／needs_information／ready_for_review，均不是批准或交易指令。篩選階段列 Candidate List 與研究理由，不冒充完成深度研究。

## 2. Business / Fund Overview

公司：客戶、產品、收入／成本與價值驅動。ETF：投信、目標、策略／指數、資產與複製結構。只採用選定資產的 Skill 分支。

## 3. Investment Thesis

| 支柱 ID | 主張與因果機制 | 事實／推論／假設／未知 | 支持來源 | 最強反證 |
|---|---|---|---|---|

## 4. Industry and Competitive Analysis

產業鏈位置、利潤池、同業比較及選取理由；ETF 則為同類基金／指數曝險比較，不直接替基金建立公司護城河。

## 5. Fundamental or ETF Structure Analysis

公司使用財務與治理分析；ETF 使用持股、集中、費用、追蹤／主動績效、流動性及配息來源。引用 period／單位／來源 ID，不混用兩種分析路徑。

## 6. Valuation or Fund Pricing / Structure Assessment

公司：適合估值方法、安全邊際、敏感性、可重算輸入與計算狀態；沒有資料則不估值。ETF：NAV 時點、價格、折溢價、費後追蹤／同類比較及結構風險；禁止套基金自身 DCF。

## 7. Bull / Base / Bear Scenarios

| 情境 | 價值驅動／假設 | 來源／反證 | 估值或曝險／結構影響 | 期限與限制 |
|---|---|---|---|---|
| Bull | | | | |
| Base | | | | |
| Bear | | | | |

ETF 情境評估底層曝險、利率／匯率、費用、追蹤與流動性等，不硬造公司 EPS 或目標價。無概率依據不填概率，資料不足不填假數字。

## 8. Risks and Counterarguments

事件／因子 ID、傳導路徑、支持與反對證據、可能影響、未建模風險。多來源同事件只算一次，互斥情境不加總。

## 9. Thesis Invalidation Criteria

| criterion_id | 支柱 ID | 條件 | KPI／質性證據 | 觀察窗口 | 證據來源 | 人工重評動作 |
|---|---|---|---|---|---|---|

## 10. Monitoring KPIs

| kpi_id／名稱 | 單位／頻率 | 來源 | operator／threshold | 門檻理由／證據 | 觀察窗口 | freshness | 缺資料處理 |
|---|---|---|---|---|---|---|---|

未有依據的門檻用 null、status=unconfigured；不能把主觀數字說成已核准政策。明列質性 trigger；提案只請求使用者重評，無自動處分。

## 11. Data Quality and Missing Information

狀態、缺欄位、衝突與採用理由、時間／幣別／口徑限制；可用工具與已執行計算，未執行項目、待取資料及下次檢查。資料品質信心不等於獲利概率。

## 12. Sources and Reporting Dates

| source_id | 提供者／文件與定位 | period | 公告日期／時間精度 | 擷取時間 | 使用欄位／主張 |
|---|---|---|---|---|---|

## 13. Skill Version / Git Commit SHA

manifest hash、canonical Skill 路徑／revision／SHA-256、完整 research_commit_sha、Mode A/B、收件清單及 hash 檢查方式、origin 驗證限制。列出實際讀過的文件與能力；不以收件代表執行。附同名 Thesis Proposal JSON 與驗證結果（結構／來源一致性／投資準確性分列），無批准紀錄。


## 14. Investment Decision

請按 company-research 的三閘門與反方審查完成本節；與 proposal.investment_decision 一致。這是研究建議，非人工批准或交易指令。

| 欄位 | 判斷／證據／缺口 |
|---|---|
| Asset Quality Status | 產品／指數、已驗證總費用、追蹤、規模／流動性與結構 |
| Entry Attractiveness Status | 現價／NAV、底層估值、費後含息報酬及風險；不要以基金合格代替進場合理 |
| Portfolio Suitability Status | 期間／風險／用款／穿透重疊；未提供個人資料必須 Not Assessed |
| Decision Status | Invest Now / Phased Entry / Wait for Conditions / Avoid / Insufficient Evidence |
| Confidence and Evidence Coverage | 已核對／必要項目與比例、來源限制；不是勝率 |
| Recommended Next Action | 具體補證、重評或條件性研究建議；不下單 |
| Entry / Reassessment Conditions | 穩定 condition_id、可觀察條件、來源、關聯 kpi_id、未來人工重評動作 |
| Bull / Base / Bear Return Scenarios | H 年、逐項輸入假設／來源、公式、累積／年化總報酬與 break-even；不足處 null |
| Downside Risk | 歷史回撤／波動與前瞻情境分開；未建模風險與最大損失限制 |
| Key Evidence That Could Change the Decision | 哪個估值／成長／成本／匯率／個人資訊會翻轉決策，如何取得 |

比較 Now／Phased／Wait：立即市場曝險、時點集中、現金拖累、成本、錯失上漲與等待條件；沒有分批現金流時不編 IRR。列同目標替代與實際總費用資料／日期，沒有資料就不宣稱更便宜。

最後逐題附反方答案與來源：為何不投資、現在進場最可能的錯、其他選擇、歷史是否被當承諾、翻轉假設、證據是否支持推薦、等待後何時重評。標示未解爭點及對決策的降級影響。
