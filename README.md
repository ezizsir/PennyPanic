# PennyPanic_bot

> I taught myself to trade by building the whole machine — the backtester, the live trader, the data pipeline, and the Telegram bot that watched the market for me. No trading frameworks. Every layer is hand-rolled.

## Why this exists

Most people who want to learn quant trading download a backtesting library, run someone else's strategy, and look at an equity curve. I didn't want the curve — I wanted to understand *why* the curve looks the way it does. So I built this from scratch: my own simulator, my own execution layer against Binance USDⓈ-M futures, my own rate-limit accounting, and my own state machine for keeping the bot's memory straight between Telegram commands.

It hunts a very specific target: **penny-tier USDT perpetual futures** — the cheap, fast, violent corner of the market where a small account can actually move the needle. The name says it: panic at the penny level, entry on structure breaks, out before the crowd figures out what happened.

## The strategy

The signal chain evolved over months of iteration, and every filter in it exists because a version without it lost money:

1. **Market structure** — `smartmoneyconcepts` detects swing highs/lows, then **Break of Structure (BoS)** events. A confirmed close beyond structure is the raw entry trigger.
2. **EMA stack discipline** — EMA8/21/55 must be layered in trend order. Price sitting between EMA8 and EMA21 after the break = a controlled pullback, not a breakdown.
3. **Purity check** — if price ever pierced the wrong side of EMA21 between the structure start and the break, the setup is discarded. Sloppy structure = no trade.
4. **BoS must be the extreme** — the breaking candle has to hold the highest high (or lowest low) since the last EMA cross. Chasing mid-range breaks gets you sold into.
5. **Dynamic leverage** — leverage is *computed per trade* from the distance to the structure extreme, so every position risks the same sliver of capital (~2%) regardless of how wide the setup is. SL/TP are then placed at fixed 2%/5% *account* risk.
6. **Liquidity gate** — the candle's USDT volume must clear the leveraged position size, so the bot only trades markets deep enough to absorb the fill.

I traded the early versions live, watched them fail in specific ways, and turned each failure into a filter. The EMA55-confirmation variant (`CheckJackpot_ema55.py` → `HistoryCheckEMA55_conf_1year.py`) is the one that survived.

## The results — one full year, 339 tickers

I pulled and cleaned **15-minute klines for every Binance USDⓈ-M futures pair for a full year** (`futures.txt`, 339 tickers), then ran the final strategy across all of it:

| Metric | Value |
|---|---|
| Backtested trades | **24,027** |
| Win rate | 37.2% |
| Payoff ratio (avg win / avg loss) | **1.81** |
| Avg win / avg loss (per-trade, leveraged) | +4.36% / −2.41% |
| Cumulative per-trade PnL over the year | **+25.6 (~2,500% on the simmed capital)** |

A 37% win rate sounds bad until you see the payoff ratio — this system is designed to lose small, often, and win big, rarely. The raw trade log is in `year_unconfirmed_variablePnL.csv` if you want to audit it yourself: every entry has a timestamp, ticker, per-trade PnL, and running total. The 1-year backtest run lives in `main.py`, driven off CSVs cached by `storage.py`.

## What I hand-built

- **Backtest simulator** (`HistoryCheckEMA55_conf_1year.py`, `BacktestFunctions.py`) — walks every historical BoS event, replays the filter chain candle by candle, simulates the position to SL or TP, and computes leveraged PnL per trade. Includes a binary-search "last crossover" lookup and a terminal progress bar for the 339-ticker sweep.
- **Live trader** (`orders.py` — 22 functions) — raw signed HMAC-SHA256 requests against Binance Futures: market/limit/stop-limit orders, SL/TP brackets, leverage + margin mode management, position polling, exchange precision (tickSize/stepSize) handling, and a `combo()` orchestrator that bundles an entry into one atomic flow. Plus active-position tracking and trailing stop-loss updates.
- **Live scanner** (`HTMLAutoRequest.py`, `CheckJackpot.py`) — polls the live 15m klines for all tickers, tracks Binance's request-weight budget per minute (with a self-resetting counter and 429/418 Retry-After handling), and fires the same filter chain in real time.
- **Telegram control plane** (`development/PennyPanic_v2.py`) — a prototype bot where `/run` and `/cancel` managed per-chat scan jobs through `python-telegram-bot`'s job queue. All the scan state — active positions, duplicate-entry guards, temporary-ignore lists with delayed removal — was handled manually with threads and timers, because I hadn't learned proper state stores yet. That was the point.
- **Data pipeline** (`storage.py`, `setdefaults.py`) — OHLCV normalization from raw Binance responses, EMA pre-computation with TA-Lib, per-ticker CSV caching, and account-wide leverage defaults.

## The honest engineering lessons

Building this solo taught me things a course never would:

- **State management is the real problem.** The trading logic was maybe 30% of the work. The other 70% was "which tickers am I in, which am I ignoring, which entry was a duplicate, and what happens when the process restarts."
- **Rate limits are a system design constraint, not an error message.** Budgeting request weight per minute across a 339-ticker scan loop changed how I structure loops forever.
- **Backtests lie quietly.** My first simulator had a lookahead bug and showed gorgeous numbers. Catching it forced me to rebuild the replay logic candle-by-candle instead of vectorizing blindly.
- **Risk math beats signal quality.** The dynamic-leverage normalization (risk the same % on every trade, whatever the structure width) did more for the equity curve than any filter I added.

## What I'd do differently

Proper state store (SQLite) instead of in-memory lists, async I/O instead of threads, pytest coverage on the PnL math, and CI. I'm keeping this repo as-is on purpose — it's a snapshot of how far self-taught gets you, and the next repo shows what I learned from it.

## Running it

```bash
pip install -r requirements.txt          # TA-Lib must be installed at the system level
cp .env.example .env                     # then add your keys — .env is gitignored
python main.py                           # 1-year backtest sweep (needs yearData/ CSVs)
python HTMLAutoRequest.py                # live scanner
```

The backtest reads per-ticker CSVs from a `yearData/` directory (built by the data pipeline); `main.py` points at that path.

## Disclaimer

Educational project. This is my engineering diary, not financial advice. It traded real money in small sizes while I learned — assume any strategy here is wrong until your own data says otherwise.

---
*Solo project: strategy research, backtesting, live execution, data engineering, and bot ops — all self-taught.*
