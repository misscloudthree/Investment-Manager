# Investment Manager｜ChatGPT 投資經理

這個 Repository 目前僅保留 **Mode 4 的每日台股資料管線、v4.1 前瞻 PAPER 研究引擎，以及 REAL / PAPER 交易帳本**。Mode 1–3（機會發掘、個股決策、持倉風險）直接依 ChatGPT Project Instructions 使用，不再要求 Codex Skills / Handoff / Schema / Mock 測試作為前置步驟。

## 現行系統
- **GitHub Actions**：`.github/workflows/mode4-data.yml`，週一至週五台灣時間約 17:10 自動取數、計算；工作流程可能延遲，台股休市日需檢查資料日期。
- **行情**：`mode4_fetch.py` → `data/mode4_latest.json`；第三方 Yahoo Finance，非交易所核驗。
- **研究及前瞻紙上交易**：`mode4_v41_engine.py` → `data/mode4_v41_engine.json`、`data/mode4_v41_paper.json`。
- **交易紀錄**：`data/mode4_trade_ledger.json`，保留已確認實際交易及人工回報，與 PAPER 模擬分帳。
- **交易規則**：`docs/mode4_v4_policy.md`、`docs/mode4_v41_status.md`。
- **補充資產觀察池**：`data/mode4_additional_pool.json`（研究用，尚未納入自動取數）。

## 重要邊界
v4.1 固定訊號與前瞻紙上模型**不等於已驗證的正期望值策略**。歷史跨市場回測、樣本外驗證、零股盤中真實撮合與事件全面核驗尚未完成；不能將模型成交當成真實券商成交。使用者回報的真實交易只在確認後更新 ledger。

## 執行
GitHub Actions → **Mode4 Daily OHLCV** → Run workflow（選 main）。部署後讀取三個 JSON 驗收日期、覆蓋、資料品質、紙上淨值。

## 清理記錄
過去未完成的 Codex Skill / 批次研究 / Schema / Mock 工程已從 main 移除。清理前完整狀態保留於分支 `archive/pre-chatgpt-cleanup-20261028`，如需復原可由該分支擷取。此 Repo 並非 Mode 1–3 唯一研究資料來源。
