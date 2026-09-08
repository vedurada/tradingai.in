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

interface Overview {
  nifty: Quote;
  banknifty: Quote;
  sensex: Quote;
  vix: Quote;
  market_status: string;
  timestamp: string;
  global_markets: Record<string, Quote>;
}

export default function Home() {
  const [data, setData] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await fetch("/api/v1/market/overview");
        if (!res.ok) throw new Error("Failed to fetch");
        const json = await res.json();
        setData(json);
        setError(null);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="p-6 text-[#94a3b8]">Loading market data...</div>;
  if (error) return <div className="p-6 text-[#ef4444]">Error: {error}</div>;
  if (!data) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div className="card col-span-1 md:col-span-2 lg:col-span-3">
        <h1 className="text-3xl font-bold mb-2">TradingAI</h1>
        <p className="text-[#94a3b8]">Financial Market Intelligence Platform</p>
      </div>
      <div className="card">
        <h2 className="section-title">NIFTY</h2>
        <div className="text-4xl font-bold text-[#e2e8f0]">{data.nifty.price.toLocaleString()}</div>
        <div className={data.nifty.change >= 0 ? "text-[#22c55e] font-semibold" : "text-[#ef4444] font-semibold"}>
          {data.nifty.change >= 0 ? "+" : ""}{data.nifty.change} ({data.nifty.change_pct}%)
        </div>
      </div>
      <div className="card">
        <h2 className="section-title">BANKNIFTY</h2>
        <div className="text-4xl font-bold text-[#e2e8f0]">{data.banknifty.price.toLocaleString()}</div>
        <div className={data.banknifty.change >= 0 ? "text-[#22c55e] font-semibold" : "text-[#ef4444] font-semibold"}>
          {data.banknifty.change >= 0 ? "+" : ""}{data.banknifty.change} ({data.banknifty.change_pct}%)
        </div>
      </div>
      <div className="card">
        <h2 className="section-title">SENSEX</h2>
        <div className="text-4xl font-bold text-[#e2e8f0]">{data.sensex.price.toLocaleString()}</div>
        <div className={data.sensex.change >= 0 ? "text-[#22c55e] font-semibold" : "text-[#ef4444] font-semibold"}>
          {data.sensex.change >= 0 ? "+" : ""}{data.sensex.change} ({data.sensex.change_pct}%)
        </div>
      </div>
      <div className="card">
        <h2 className="section-title">India VIX</h2>
        <div className="text-4xl font-bold text-[#e2e8f0]">{data.vix.price.toFixed(2)}</div>
        <div className={data.vix.change >= 0 ? "text-[#22c55e] font-semibold" : "text-[#ef4444] font-semibold"}>
          {data.vix.change >= 0 ? "+" : ""}{data.vix.change} ({data.vix.change_pct}%)
        </div>
      </div>
      <div className="card">
        <h2 className="section-title">Market Status</h2>
        <div className="market-status-live mt-2">{data.market_status}</div>
      </div>
    </div>
  );
}