# Investment Memo — <名稱／asset_id>

模板版本：1.0；此文件只規定呈現與索引，分析步驟以 manifest 指定的 SKILL.md 為準。每節保留，有資料不足或不適用時說明理由。公開／匿名文件才進 Git，私人資料另存指定受控位置。

## 1. Executive Summary

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
