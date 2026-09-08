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

export default function StocksPage() {
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await fetch("/api/v1/market/overview");
        if (!res.ok) throw new Error("Failed");
        const data = await res.json();
        setQuotes([data.nifty, data.banknifty, data.sensex]);
      } catch {
        // keep empty
      } finally {
        setLoading(false);
      }
    }
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="p-6 text-[#94a3b8]">Loading stocks...</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Stocks</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {quotes.map((q) => (
          <div key={q.symbol} className="card">
            <h2 className="section-title">{q.symbol}</h2>
            <div className="text-3xl font-bold">{q.price.toLocaleString()}</div>
            <div className={q.change >= 0 ? "text-[#22c55e] font-semibold" : "text-[#ef4444] font-semibold"}>
              {q.change >= 0 ? "+" : ""}{q.change} ({q.change_pct}%)
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}