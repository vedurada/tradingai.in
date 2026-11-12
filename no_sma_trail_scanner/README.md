# NO-SMA Trail Trail Scanner

Trailing-stop variant of the no_sma scanner. Entry signals are consumed from the base no_sma scanner's live open position (same contract, price and entry candle); this scanner only owns the exit, which is a 5-point trailing stop (activates at +5, stop = peak - 5) or the entry-candle close.

Database: /opt/tradingai/database/no_sma_trail.db
Service: tradingai-no-sma-trail-scanner
API: /api/no-sma-trail/*
Dashboard: https://tradingai.in/live/no-sma-trail/

## Rate-limit hardening

- Staggered 5s tick (offset 4.2s) so scanners do not hit Kite together.
- One local base-status HTTP call per tick; no Kite quota is used.
- One batched quote call per tick (NIFTY spot + CE + PE legs).
- Trail-stop exit uses the live LTP only; no historical call.
- Historical candles are fetched only for the entry-candle close exit.
- Historical lookback is 1 day, widened to 3 days only when too few candles are returned (weekends/holidays).
