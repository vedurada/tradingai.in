"use client";

import { useEffect, useState } from "react";

export default function AIPage() {
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await fetch("/api/v1/ai/market-view");
        if (!res.ok) throw new Error("Failed");
        setAnalysis(await res.json());
      } catch {
        // keep stale
      } finally {
        setLoading(false);
      }
    }
    fetchData();
    const interval = setInterval(fetchData, 300000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="p-6 text-[#94a3b8]">Loading AI analysis...</div>;
  if (!analysis) return null;

  const isBullish = analysis.market_view === "BULLISH";
  const isBearish = analysis.market_view === "BEARISH";

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">AI Intelligence</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="section-title">AI Market View</h2>
          <div className="mt-4">
            <div className={`text-6xl font-bold ${isBullish ? "text-[#22c55e]" : isBearish ? "text-[#ef4444]" : "text-[#eab308]"}`}>
              {analysis.market_view}
            </div>
            <p className="text-[#94a3b8] mt-2">Confidence: {analysis.confidence}%</p>
          </div>
          <div className="mt-6 space-y-3">
            <h3 className="font-semibold text-[#22c55e]">Analysis</h3>
            <ul className="space-y-2 text-sm">
              {analysis.reasons_bullish?.map((r: string, i: number) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-[#22c55e]">✓</span>
                  <span className="text-[#94a3b8]">{r}</span>
                </li>
              ))}
              {analysis.reasons_bearish?.map((r: string, i: number) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-[#ef4444]">✗</span>
                  <span className="text-[#94a3b8]">{r}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div className="card">
          <h2 className="section-title">Key Risks</h2>
          <div className="mt-4 space-y-3">
            {analysis.reasons_bearish?.map((r: string, i: number) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-[#f59e0b]">⚠</span>
                <span className="text-[#94a3b8] text-sm">{r}</span>
              </div>
            ))}
            {analysis.signals?.map((s: string, i: number) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-[#3b82f6]">ℹ</span>
                <span className="text-[#94a3b8] text-sm">{s}</span>
              </div>
            ))}
            <div className="flex items-start gap-2">
              <span className="text-[#94a3b8]">ℹ</span>
              <span className="text-[#94a3b8] text-sm">VIX Level: {analysis.vix_level}</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-[#94a3b8]">ℹ</span>
              <span className="text-[#94a3b8] text-sm">PCR Signal: {analysis.pcr_signal}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}