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

const INDICES = ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX"];

export default function MarketsPage() {
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await fetch("/api/v1/market/overview");
        if (!res.ok) throw new Error("Failed");
        const data = await res.json();
        setQuotes({
          nifty: data.nifty,
          banknifty: data.banknifty,
          sensex: data.sensex,
        });
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

  if (loading) return <div className="p-6 text-[#94a3b8]">Loading indices...</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Indian Indices</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {INDICES.map((symbol) => (
          <div key={symbol} className="card">
            <h2 className="section-title">{symbol}</h2>
            <div className="text-3xl font-bold text-[#e2e8f0]">
              {quotes[symbol.toLowerCase()]?.price?.toLocaleString() || "-"}
            </div>
            <div
              className={`text-sm font-semibold ${quotes[symbol.toLowerCase()]?.change >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"}`}
            >
              {quotes[symbol.toLowerCase()]?.change >= 0 ? "+" : ""}
              {quotes[symbol.toLowerCase()]?.change?.toFixed(2) || "-"} (
              {quotes[symbol.toLowerCase()]?.change_pct?.toFixed(2) || "-"}%)
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}