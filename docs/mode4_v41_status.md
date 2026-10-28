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
