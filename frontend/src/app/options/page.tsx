"use client";

import { useEffect, useState } from "react";

interface OptionsIntelligence {
  symbol: string;
  pcr: number;
  call_oi: number;
  put_oi: number;
  max_pain: {
    max_pain: number;
    call_max_oi_strike: number;
    put_max_oi_strike: number;
  };
  iv_stats: {
    avg_iv: number;
    min_iv: number;
    max_iv: number;
    iv_rank: number;
  };
  environment: string;
  strategy_classes: string[];
  timestamp: string;
  data_unavailable?: boolean;
  message?: string;
}

export default function OptionsPage() {
  const [data, setData] = useState<OptionsIntelligence | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await fetch("/api/v1/options/intelligence?symbol=NIFTY")
        if (!res.ok) throw new Error("Failed")
        setData(await res.json())
        setError(null)
      } catch {
        setError("Unable to fetch options data")
      } finally {
        setLoading(false)
      }
    }
    fetchData()
    const interval = setInterval(fetchData, 300000)
    return () => clearInterval(interval)
  }, [])

  if (loading)
    return (
      <div className="p-6 text-[#94a3b8]">Loading options intelligence...</div>
    )

  if (error || !data)
    return (
      <div className="p-6 text-[#ef4444]">
        Error: {error || "No data"}
        <div className="mt-2 text-sm text-[#94a3b8]">
          Data unavailable — check API connectivity
        </div>
      </div>
    )

  if (data.data_unavailable)
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-[#e2e8f0] mb-4">
          Options Intelligence
        </h1>
        <div className="card">
          <p className="text-[#94a3b8]">{data.message}</p>
          <p className="text-xs text-[#94a3b8] mt-4">
            Data source: Yahoo Finance (no Indian options data available)
          </p>
        </div>
      </div>
    )

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-[#e2e8f0]">
        Options Intelligence — {data.symbol}
      </h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="text-xs text-[#94a3b8]">PCR</div>
          <div className="text-2xl font-bold text-[#e2e8f0]">
            {data.pcr.toFixed(3)}
          </div>
          <div className="text-xs text-[#94a3b8] mt-1">
            {data.pcr > 1.3
              ? "Put-heavy"
              : data.pcr < 0.8
                ? "Call-heavy"
                : "Balanced"}
          </div>
        </div>
        <div className="card">
          <div className="text-xs text-[#94a3b8]">Call OI</div>
          <div className="text-2xl font-bold text-[#22c55e]">
            {data.call_oi.toLocaleString()}
          </div>
        </div>
        <div className="card">
          <div className="text-xs text-[#94a3b8]">Put OI</div>
          <div className="text-2xl font-bold text-[#ef4444]">
            {data.put_oi.toLocaleString()}
          </div>
        </div>
        <div className="card">
          <div className="text-xs text-[#94a3b8]">Max Pain</div>
          <div className="text-2xl font-bold text-[#e2e8f0]">
            {data.max_pain.max_pain.toFixed(2)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="card">
          <h2 className="text-lg font-bold text-[#e2e8f0] mb-2">
            IV Statistics
          </h2>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-[#94a3b8]">Avg IV</span>
              <span className="text-[#e2e8f0]">
                {data.iv_stats.avg_iv.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#94a3b8]">Min IV</span>
              <span className="text-[#e2e8f0]">
                {data.iv_stats.min_iv.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#94a3b8]">Max IV</span>
              <span className="text-[#e2e8f0]">
                {data.iv_stats.max_iv.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#94a3b8]">IV Rank</span>
              <span className="text-[#e2e8f0]">
                {data.iv_stats.iv_rank.toFixed(1)}%
              </span>
            </div>
          </div>
        </div>

        <div className="card">
          <h2 className="text-lg font-bold text-[#e2e8f0] mb-2">
            Market Environment
          </h2>
          <div className="text-2xl font-bold text-[#e2e8f0]">
            {data.environment}
          </div>
          <div className="mt-3">
            <div className="text-xs text-[#94a3b8] mb-1">
              Strategy Classes:
            </div>
            <div className="flex flex-wrap gap-2">
              {data.strategy_classes.map((sc, i) => (
                <span key={i} className="badge badge-blue">
                  {sc}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="text-xs text-[#94a3b8] text-center py-4">
        Last updated:{" "}
        {new Date(data.timestamp).toLocaleString("en-IN", {
          timeZone: "Asia/Kolkata",
        })}
      </div>
    </div>
  )
}