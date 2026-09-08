"use client";

import { useEffect, useState } from "react";

interface Overview {
  nifty: { symbol: string; price: number; change: number; change_pct: number };
  banknifty: { symbol: string; price: number; change: number; change_pct: number };
  sensex: { symbol: string; price: number; change: number; change_pct: number };
}

export default function MarketsPage() {
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

  if (loading) return <div className="p-6 text-[#94a3b8]">Loading markets...</div>;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Markets</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="card">
          <h2 className="section-title">NIFTY 50</h2>
          <div className="text-3xl font-bold">{data.nifty.price.toLocaleString()}</div>
          <div className={data.nifty.change >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"}>
            {data.nifty.change >= 0 ? "+" : ""}{data.nifty.change} ({data.nifty.change_pct}%)
          </div>
        </div>
        <div className="card">
          <h2 className="section-title">BANKNIFTY</h2>
          <div className="text-3xl font-bold">{data.banknifty.price.toLocaleString()}</div>
          <div className={data.banknifty.change >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"}>
            {data.banknifty.change >= 0 ? "+" : ""}{data.banknifty.change} ({data.banknifty.change_pct}%)
          </div>
        </div>
        <div className="card">
          <h2 className="section-title">SENSEX</h2>
          <div className="text-3xl font-bold">{data.sensex.price.toLocaleString()}</div>
          <div className={data.sensex.change >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"}>
            {data.sensex.change >= 0 ? "+" : ""}{data.sensex.change} ({data.sensex.change_pct}%)
          </div>
        </div>
      </div>
    </div>
  );
}