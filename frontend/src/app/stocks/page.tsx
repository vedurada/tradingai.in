"use client";

import { useEffect, useState } from "react";

interface Quote {
  symbol: string;
  price: number;
  change: number;
  change_pct: number;
  open: number;
  high: number;
  low: number;
  previous_close: number;
  volume: number;
  market_status: string;
}

const FOS_STOCKS = [
  "RELIANCE", "HDFCBANK", "ICICIBANK", "SBIN", "INFY", "TCS", "LT",
  "AXISBANK", "ADANIENT", "BHARTIARTL", "BEL", "HDFC", "HDFCLIFE",
  "ICICIGI", "KOHLERBD", "M&M", "MARUTI", "NTPC", "POWERGRID",
  "TATAMOTORS", "TATASTEEL", "WIPRO", "TECHM", "BAJAJ-AUTO",
  "BAJFINANCE", "BAJAJFINSV", "SUNPHARMA", "ULTRACEMCO", "GRASIM",
  "HEROMOTOCO", "BPCL", "IOC", "ONGC", "GAIL", "COALINDIA",
  "CANBK", "PNB", "UNIONBANK", "KOTAKBANK", "INDUSINDBK",
  "DIVISLAB", "DRREDDY", "CIPLA", "ASHOKLEY", "TORNTPHARM",
];

export default function StocksPage() {
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [overviewRes, niftyRes] = await Promise.all([
          fetch("/api/v1/market/overview"),
          fetch("/api/v1/market/nifty"),
        ]);
        const overview = overviewRes.ok ? await overviewRes.json() : null;
        const nifty = niftyRes.ok ? await niftyRes.json() : null;
        const allQuotes: Record<string, Quote> = {};
        if (overview) {
          if (overview.nifty) allQuotes["NIFTY"] = overview.nifty;
          if (overview.banknifty) allQuotes["BANKNIFTY"] = overview.banknifty;
          if (overview.sensex) allQuotes["SENSEX"] = overview.sensex;
        }
        if (nifty) allQuotes["NIFTY"] = nifty;
        setQuotes(allQuotes);
      } catch {
        // keep empty
      } finally {
        setLoading(false);
      }
    }
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="p-6 text-[#94a3b8]">Loading F&O stocks...</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">F&O Stocks</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {FOS_STOCKS.map((symbol) => (
          <div key={symbol} className="card">
            <h2 className="section-title">{symbol}</h2>
            <div className="text-3xl font-bold text-[#e2e8f0]">
              {quotes[symbol]?.price?.toLocaleString() || "-"}
            </div>
            <div
              className={`text-sm font-semibold ${quotes[symbol]?.change >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"}`}
            >
              {quotes[symbol]?.change >= 0 ? "+" : ""}
              {quotes[symbol]?.change?.toFixed(2) || "-"} (
              {quotes[symbol]?.change_pct?.toFixed(2) || "-"}%)
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}