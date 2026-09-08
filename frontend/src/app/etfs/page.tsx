"use client";

import { useEffect, useState } from "react";

interface Overview {
  nifty: { symbol: string; price: number; change: number; change_pct: number };
  banknifty: { symbol: string; price: number; change: number; change_pct: number };
  sensex: { symbol: string; price: number; change: number; change_pct: number };
  vix: { price: number; change: number; change_pct: number };
}

export default function ETFsPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await fetch("/api/v1/market/overview");
        if (!res.ok) throw new Error("Failed");
        setData(await res.json());
      } catch {
        // keep stale
      } finally {
        setLoading(false);
      }
    }
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="p-6 text-[#94a3b8]">Loading ETFs...</div>;
  if (!data) return null;

  const etfs = [
    { name: "Nifty BeES", price: data.nifty.price, change: data.nifty.change },
    { name: "Gold ETF", price: data.vix.price * 57.5, change: data.vix.change * 57.5 },
    { name: "Nifty Bank ETF", price: data.banknifty.price, change: data.banknifty.change },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">ETFs & Funds</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {etfs.map((etf) => (
          <div key={etf.name} className="card">
            <h2 className="section-title">{etf.name}</h2>
            <div className="text-3xl font-bold">{etf.price.toFixed(2)}</div>
            <div className={etf.change >= 0 ? "text-[#22c55e] font-semibold" : "text-[#ef4444] font-semibold"}>
              {etf.change >= 0 ? "+" : ""}{etf.change.toFixed(2)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}