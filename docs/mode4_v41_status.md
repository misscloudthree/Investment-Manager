# Mode 4 v4.1 implementation status
Date: 2026-10-28 Asia/Taipei.
Inherits docs/mode4_v4_policy.md. The research engine lives in mode4_v41_engine.py and the daily automation in .github/workflows/mode4-data.yml.

Daily expected outputs:
- data/mode4_v41_engine.json: deterministic breakout, pullback, mean-reversion research candidates and data-quality exclusions
- data/mode4_v41_paper.json: independent forward PAPER simulation, cash, modeled transactions and daily equity
- data/mode4_latest.json: market data snapshot

PAPER has TWD100000 initial capital, TWD400 risk per transaction, one simultaneous position and no leverage. A signal is not proof of positive expectancy. Entries modeled at next session open only if within limit and above stop, with slippage. Stops and time exits are modeled. Touching a target in OHLC is not automatically marked filled because intraday sequence is unavailable. Events are model fills, never real brokerage execution.

REAL holdings and user reports remain exclusively in data/mode4_trade_ledger.json, including the historical 2881 100 shares at 161 record. The script never modifies REAL.

Important remaining gaps: historical backtesting, walk-forward out-of-sample validation, historical point-in-time C-universe selection, exchange validation and intraday/odd-lot execution realism are NOT implemented. Current 90-bar historical snapshot is insufficient to substantiate historical statistical advantage. Do not claim positive expectancy or a proven 2-5 trades per week.

The GitHub Actions change has been committed, but it must run successfully before the new JSON output can be called deployed.

## v4.1.1 — 精簡 A/B 均值回歸比較（2026-10-29）
保留現有三種策略 BREAKOUT、PULLBACK、MEAN_REVERSION；A/B 是 MEAN_REVERSION 的兩個進場版本，**不是新增第四策略**。由 `mode4_v41_engine.py` 在原本的兩份 JSON 內擴充 `ab_comparison` 與 `ab_shadow_accounts`，不新增第三個研究輸出檔或新排程。

- **A 積極低接（早進場）**：跌深均值回歸研究訊號當天收盤成立後，下一個交易日只有在「開盤價 <= 研究最高限價，且開盤價 > 停損價」時才模擬買進；若跳空漲過上限不追價。K線收盤位置與下影線作為反轉強弱**輔助標籤**，不增加一串硬性門檻。A 旨在測試較早進場是否能獲得更多可成交機會，不代表高勝率。
- **B 反彈確認（較晚進場）**：針對**同一個基礎訊號**，下一交易日「收盤價 > 訊號日最高價，且收盤價 > 當日開盤價」才在盤後確認；最早是再下一交易日開盤符合限價才模擬買進。未確認、或確認後已超過合理目標價，視為未成交／錯失機會，不能事後改寫進場價格。
- **公平比較**：A/B 各有獨立虛擬 NT$100,000（**並非合計新增可投入 NT$200,000**），單筆含估計成本風險上限約 NT$400、最多一個持倉、相同來源訊號和持有時限，記錄拒絕、未成交、交易次數、淨值、已實現及最大回撤。新帳戶從部署後下一完整有效交易日**前瞻開始**，舊單一 PAPER 及歷史 REAL 均保留但不回填到 A/B。
- **面向使用者的單張卡**：標示 `A｜積極低接：BUY SETUP / 觀察`、`B｜確認反彈：等待確認 / BUY SETUP`。每版最多一個重點股票、限價、數量、停損停利、最大假設淨虧損、日期；有差別才附一行解釋。用戶自行決定 REAL 買賣並回報，GitHub 不代下單。
- **不可虛構優勢**：BUY SETUP 只是可研究進場方案，並非真實下單核准或已證實正期望值。日 K 開盤成交、成交稅費與零股滑價是模型假設；重大公告及盤中撮合資料尚未完整驗證。股票跳動單位按簡易區間近似，ETF 用 0.01 研究用近似，**真實下單前應另外核對交易所跳動單位**。
- **部署驗收**：程式及提示詞修改已提交，但新的 `ab_comparison`/`ab_shadow_accounts` 必須由下一次成功 GitHub Actions 執行產出，且應檢查 A/B 事件不重複、日期不回填、REAL 交易帳本不被更動。未看到欄位前不要宣稱新模型已有 PAPER 交易或獲利。

仍未實作：跨週期回測、walk-forward、樣本外驗證、完整公司行動調整、盤中真實撮合及券商費率核對。對使用者不應輸出工程欄位表取代決策卡。
