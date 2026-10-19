# 必備資料契約（供 AI 實作 connector 使用）

## Quote
- `asset_id`: 交易所代碼＋市場，例 `TWSE:2330`，避免同名代碼衝突
- `asset_type`: equity, etf, mutual_fund, cash
- `as_of`: 發布資料所屬日期（不是電腦執行時間）
- `close`: 當期可比較價格；`prev_close`: 前期同基礎價格，幣別相同，調整股票分割與除權息比較口徑
- `source_url`, `published_at`, `retrieved_at`, `price_basis`, `currency`
- `mode`: live or demo; demo 永遠不可用於對外報告

## Event
- `id`, `asset_ids`, `published_at`, `data_as_of`, `headline`, `source_url`, `severity` (info/watch/high), `category` (company/industry/macro), `verified` (bool), `impact_path`, `expected_kpi`, `expires_at`
- 消息要去重，區分事件日期/公告日期/抓取日期，不確定標示 `UNVERIFIED`。

## Thesis / Portfolio
- 資產設定：status (watchlist/candidate/held/closed)、asset_type、實際已確認的 target_weight_pct/actual_weight_pct、版次
- Thesis：base_thesis、KPI 名稱/來源/門檻/觀察頻率、invalidation_condition、review_due_at、owner、批准時間
- 基金：基金名稱、ISIN、NAV 幣別與公告時間、管理費/總費用、持股揭露頻率、底層區域與產業曝險；未知曝險不得假定為 0
- 所有更新須 append-only audit log 及明確 human approval。

## 優先資料來源
- TWSE OpenAPI: https://openapi.twse.com.tw/（上市股票報價、ETF 等）
- TPEx / 公開資訊觀測站：上櫃資料與財報公告
- FinMind: https://finmind.github.io/（資料商整合；核對授權、更新時間、限制）
- TDCC OpenAPI: https://openapi.tdcc.com.tw/swagger-ui/index.html（部分基金/揭露資訊）
- 基金經理公司、官方月報：基金 NAV、持股、基準、報酬與費用
- 台灣央行、國發會、官方國際統計：利率、匯率、景氣資料

## Freshness
- 非交易日應明示 `MARKET_CLOSED`，不得視為數據缺失導致風險歸零。
- 當日資料未公布時明示 pending；境內外基金 NAV 可能滯後，不能拿 ETF 行情直接取代。
- 可靠性 gate 先行，再允許模型解讀及計算。
