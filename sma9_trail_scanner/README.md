# SMA9 Trail Trail Scanner

Trailing-stop variant of the sma9 scanner. Entry signals are consumed from the base sma9 scanner's live open position (same contract, price and entry candle); this scanner only owns the exit, which is a 5-point trailing stop (activates at +5, stop = peak - 5) or the entry-candle close.

Database: /opt/tradingai/database/sma9_trail.db
Service: tradingai-sma9-trail-scanner
API: /api/sma9-trail/*
Dashboard: https://tradingai.in/live/sma9-trail/

## Rate-limit hardening

- Staggered 5s tick (offset 1.2s) so scanners do not hit Kite together.
- One local base-status HTTP call per tick; no Kite quota is used.
- One batched quote call per tick (NIFTY spot + CE + PE legs).
- Trail-stop exit uses the live LTP only; no historical call.
- Historical candles are fetched only for the entry-candle close exit.
- Historical lookback is 1 day, widened to 3 days only when too few candles are returned (weekends/holidays).
