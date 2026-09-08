"use client";

import { useEffect, useState } from "react";

export default function TradingPage() {
  const [signals, setSignals] = useState<any[]>([]);
  const [marketView, setMarketView] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [signalsRes, viewRes] = await Promise.all([
          fetch("/api/v1/signals"),
          fetch("/api/v1/ai/market-view"),
        ]);
        if (signalsRes.ok) {
          const data = await signalsRes.json();
          setSignals(data.signals || []);
        }
        if (viewRes.ok) {
          setMarketView(await viewRes.json());
        }
      } catch {
        // keep stale
      } finally {
        setLoading(false);
      }
    }
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="p-6 text-[#94a3b8]">Loading trading intelligence...</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Trading Intelligence</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="section-title">Live Signals</h2>
          <div className="mt-4 space-y-3">
            {signals.length === 0 && (
              <p className="text-[#94a3b8] text-sm">No active signals</p>
            )}
            {signals.map((s, i) => (
              <div key={i} className={`p-3 bg-[#0a1428] rounded border-l-4 ${s.signal_type === "BUY" ? "border-[#22c55e]" : s.signal_type === "SELL" ? "border-[#ef4444]" : "border-[#eab308]"}`}>
                <div className="flex justify-between">
                  <span className="font-semibold">{s.symbol} {s.signal_type === "BUY" ? "Bullish" : s.signal_type === "SELL" ? "Bearish" : "Neutral"}</span>
                  <span className={`text-sm ${s.signal_type === "BUY" ? "text-[#22c55e]" : s.signal_type === "SELL" ? "text-[#ef4444]" : "text-[#eab308]"}`}>{s.signal_type}</span>
                </div>
                <p className="text-[#94a3b8] text-sm mt-1">Confidence: {s.confidence}%</p>
              </div>
            ))}
          </div>
        </div>
        <div className="card">
          <h2 className="section-title">Market Regime</h2>
          <div className="mt-4">
            <div className={`text-6xl font-bold ${marketView?.market_view === "BULLISH" ? "text-[#22c55e]" : marketView?.market_view === "BEARISH" ? "text-[#ef4444]" : "text-[#eab308]"}`}>
              {marketView?.market_view || "NEUTRAL"}
            </div>
            <p className="text-[#94a3b8] mt-2">Confidence: {marketView?.confidence || 0}%</p>
            <p className="text-[#94a3b8] text-sm mt-1">VIX Level: {marketView?.vix_level || "---"}</p>
            <p className="text-[#64748b] text-xs mt-3">Generated at {marketView?.generated_at || "---"}</p>
          </div>
        </div>
      </div>
    </div>
  );
}