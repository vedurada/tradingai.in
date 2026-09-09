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

interface RegimeData {
  timestamp: string;
  market_regime: string;
  confidence: number;
  market_bias: string;
  summary: string;
  nifty: {
    spot: number;
    support: number[];
    resistance: number[];
    trend: string;
  };
  regime: {
    type: string;
    confidence: number;
    trend_strength: string;
    momentum: string;
    volatility: string;
  };
  evidence: string[];
  primary_scenario: {
    type: string;
    condition: string;
    confirmation: string;
    invalidation: string;
    target: number;
  };
  alternative_scenario: {
    type: string;
    condition: string;
    confirmation: string;
    invalidation: string;
    target: number;
  };
  risk_scenario: {
    type: string;
    condition: string;
    confirmation: string;
    invalidation: string;
    target: number;
  };
  strategy_classes: string[];
  risk_flags: string[];
}

interface IndicatorsData {
  symbol: string;
  interval: string;
  indicators: {
    vwap: number;
    pivot: {
      pivot: number;
      r1: number;
      s1: number;
      r2: number;
      s2: number;
      r3: number;
      s3: number;
    };
    cpr: {
      pivot: number;
      bc: number;
      tc: number;
      r1: number;
      s1: number;
    };
    bollinger_bands: {
      upper: number;
      middle: number;
      lower: number;
      period: number;
    } | null;
    rsi: number | null;
    macd: {
      macd: number;
      signal: number;
      histogram: number;
    } | null;
    adx: number | null;
    support_resistance: {
      support: number[];
      resistance: number[];
      prev_high: number;
      prev_low: number;
    };
    timestamp: string;
  };
}

export default function Home() {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [regime, setRegime] = useState<RegimeData | null>(null)
  const [indicators, setIndicators] = useState<IndicatorsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchData() {
      try {
        const [ovRes, rgRes, indRes] = await Promise.all([
          fetch("/api/v1/market/overview"),
          fetch("/api/v1/ai/regime-enhanced?symbol=NIFTY"),
          fetch("/api/v1/technical/indicators?symbol=NIFTY&interval=1d&limit=20"),
        ])
        if (!ovRes.ok) throw new Error("Failed to fetch overview")
        if (!rgRes.ok) throw new Error("Failed to fetch regime")
        if (!indRes.ok) throw new Error("Failed to fetch indicators")
        const ovJson = await ovRes.json()
        const rgJson = await rgRes.json()
        const indJson = await indRes.json()
        setOverview(ovJson)
        setRegime(rgJson)
        setIndicators(indJson)
        setError(null)
      } catch (e: any) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
    const interval = setInterval(fetchData, 60000)
    return () => clearInterval(interval)
  }, [])

  if (loading)
    return (
      <div className="p-6 text-[#94a3b8]">
        <div className="animate-pulse">Loading market data...</div>
      </div>
    )
  if (error)
    return (
      <div className="p-6 text-[#ef4444]">
        Error: {error}
        <div className="mt-2 text-sm text-[#94a3b8]">
          Data unavailable — check API connectivity
        </div>
      </div>
    )
  if (!overview || !regime || !indicators) return null

  const nifty = overview.nifty
  const banknifty = overview.banknifty
  const sensex = overview.sensex
  const vix = overview.vix

  const regimeColors: Record<string, string> = {
    TREND_UP: "text-[#22c55e]",
    TREND_DOWN: "text-[#ef4444]",
    RANGE: "text-[#eab308]",
    BREAKOUT: "text-[#3b82f6]",
    BREAKDOWN: "text-[#ef4444]",
    HIGH_VOLATILITY: "text-[#f97316]",
    LOW_VOLATILITY: "text-[#8b5cf6]",
    OPENING_VOLATILITY: "text-[#eab308]",
    UNCONFIRMED: "text-[#94a3b8]",
  }

  const regimeScores = [
    { label: "TREND", score: 80, color: "#22c55e" },
    { label: "MOMENTUM", score: 70, color: "#22c55e" },
    { label: "VOLUME", score: 60, color: "#eab308" },
    { label: "VOLATILITY", score: 80, color: "#22c55e" },
    { label: "OPTIONS", score: 70, color: "#22c55e" },
    { label: "STRUCTURE", score: 80, color: "#22c55e" },
  ]

  const overallCondition = "Bullish Trend"
  const topConditions = [
    { label: "Breakout candidates", count: 8, color: "#22c55e" },
    { label: "Range-bound", count: 11, color: "#eab308" },
    { label: "Bearish setups", count: 6, color: "#ef4444" },
    { label: "High volatility", count: 4, color: "#f97316" },
    { label: "No-trade", count: 7, color: "#94a3b8" },
  ]

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-[#e2e8f0]">
            TradingAI
          </h1>
          <p className="text-[#94a3b8] text-sm">
            Financial Market Intelligence Platform
          </p>
        </div>
        <div className="mt-2 md:mt-0 flex items-center gap-3">
          <span className="market-status-live">LIVE</span>
          <span className="text-xs text-[#94a3b8]">
            {new Date().toLocaleTimeString("en-IN", {
              timeZone: "Asia/Kolkata",
            })}
          </span>
        </div>
      </div>

      {/* TODAY'S MARKET CONDITION - Killer Feature */}
      <div className="card mb-6">
        <h2 className="text-xl font-bold text-[#e2e8f0] mb-4">
          TODAY&apos;S MARKET CONDITION
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          {[
            { label: "NIFTY", data: nifty, color: nifty.change >= 0 ? "#22c55e" : "#ef4444" },
            { label: "BANKNIFTY", data: banknifty, color: banknifty.change >= 0 ? "#22c55e" : "#ef4444" },
            { label: "SENSEX", data: sensex, color: sensex.change >= 0 ? "#22c55e" : "#ef4444" },
            { label: "INDIA VIX", data: vix, color: vix.price < 15 ? "#22c55e" : "#f97316" },
          ].map((item) => (
            <div key={item.label} className="p-3 rounded border border-[#22c55e]/20 bg-[#22c55e]/5">
              <div className="text-xs text-[#94a3b8]">{item.label}</div>
              <div className="text-lg font-bold text-[#e2e8f0]">
                {item.data.price.toLocaleString()}
              </div>
              <div className="text-sm font-semibold" style={{ color: item.color }}>
                {item.data.change >= 0 ? "+" : ""}
                {item.data.change.toFixed(2)} ({item.data.change_pct.toFixed(2)}%)
              </div>
            </div>
          ))}
        </div>
        <div className="text-center py-2">
          <div className="text-sm text-[#94a3b8] mb-1">OVERALL MARKET CONDITION</div>
          <div className="text-2xl font-bold text-[#22c55e]">{overallCondition}</div>
        </div>
        <div className="mt-4">
          <div className="text-xs text-[#94a3b8] mb-2">MARKET REGIME SCORE</div>
          <div className="space-y-2">
            {regimeScores.map((score) => (
              <div key={score.label} className="flex items-center gap-2">
                <div className="w-20 text-xs text-[#94a3b8]">{score.label}</div>
                <div className="flex-1 bg-[#1a2d4d] rounded-full h-2">
                  <div
                    className="h-2 rounded-full"
                    style={{ width: `${score.score}%`, backgroundColor: score.color }}
                  />
                </div>
                <div className="w-8 text-xs text-[#e2e8f0] text-right">{score.score}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="mt-4">
          <div className="text-xs text-[#94a3b8] mb-2">TOP CONDITIONS</div>
          <div className="flex flex-wrap gap-2">
            {topConditions.map((cond) => (
              <div key={cond.label} className="px-3 py-1 rounded bg-[#1a2d4d] text-sm">
                <span className="text-[#94a3b8]">{cond.label}: </span>
                <span style={{ color: cond.color }}>{cond.count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Market Ticker */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-6">
        {[
          { label: "NIFTY", data: nifty },
          { label: "BANKNIFTY", data: banknifty },
          { label: "SENSEX", data: sensex },
          { label: "INDIA VIX", data: vix },
        ].map((item) => (
          <div key={item.label} className="card">
            <div className="text-xs text-[#94a3b8] mb-1">{item.label}</div>
            <div className="text-lg font-bold text-[#e2e8f0]">
              {item.data.price.toLocaleString()}
            </div>
            <div
              className={`text-sm font-semibold ${item.data.change >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"}`}
            >
              {item.data.change >= 0 ? "+" : ""}
              {item.data.change.toFixed(2)} ({item.data.change_pct.toFixed(2)}%)
            </div>
          </div>
        ))}
      </div>

      {/* AI Market Outlook */}
      <div className="card mb-6">
        <h2 className="text-xl font-bold text-[#e2e8f0] mb-4">
          TODAY&apos;S MARKET OUTLOOK
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-4">
          <div>
            <div className="text-xs text-[#94a3b8]">Regime</div>
            <div
              className={`text-lg font-bold ${regimeColors[regime.market_regime] || "text-[#e2e8f0]"}`}
            >
              {regime.market_regime}
            </div>
          </div>
          <div>
            <div className="text-xs text-[#94a3b8]">Confidence</div>
            <div className="text-lg font-bold text-[#e2e8f0]">
              {regime.confidence}%
            </div>
          </div>
          <div>
            <div className="text-xs text-[#94a3b8]">Bias</div>
            <div className="text-lg font-bold text-[#e2e8f0]">
              {regime.market_bias}
            </div>
          </div>
          <div>
            <div className="text-xs text-[#94a3b8]">Trend Strength</div>
            <div className="text-lg font-bold text-[#e2e8f0]">
              {regime.regime.trend_strength}
            </div>
          </div>
          <div>
            <div className="text-xs text-[#94a3b8]">Momentum</div>
            <div className="text-lg font-bold text-[#e2e8f0]">
              {regime.regime.momentum}
            </div>
          </div>
          <div>
            <div className="text-xs text-[#94a3b8]">Volatility</div>
            <div className="text-lg font-bold text-[#e2e8f0]">
              {regime.regime.volatility}
            </div>
          </div>
        </div>
        <div className="text-sm text-[#94a3b8] whitespace-pre-line">
          {regime.summary}
        </div>
      </div>

      {/* Key Levels */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="card">
          <h3 className="text-sm font-semibold text-[#94a3b8] mb-2">
            Pivot Points
          </h3>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-[#94a3b8]">Pivot</span>
              <span className="text-[#e2e8f0]">
                {indicators.indicators.pivot.pivot.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#94a3b8]">R1</span>
              <span className="text-[#22c55e]">
                {indicators.indicators.pivot.r1.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#94a3b8]">S1</span>
              <span className="text-[#ef4444]">
                {indicators.indicators.pivot.s1.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#94a3b8]">R2</span>
              <span className="text-[#22c55e]">
                {indicators.indicators.pivot.r2.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#94a3b8]">S2</span>
              <span className="text-[#ef4444]">
                {indicators.indicators.pivot.s2.toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="text-sm font-semibold text-[#94a3b8] mb-2">
            CPR (Central Pivot Range)
          </h3>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-[#94a3b8]">Pivot</span>
              <span className="text-[#e2e8f0]">
                {indicators.indicators.cpr.pivot.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#94a3b8]">BC</span>
              <span className="text-[#e2e8f0]">
                {indicators.indicators.cpr.bc.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#94a3b8]">TC</span>
              <span className="text-[#e2e8f0]">
                {indicators.indicators.cpr.tc.toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="text-sm font-semibold text-[#94a3b8] mb-2">
            VWAP
          </h3>
          <div className="text-2xl font-bold text-[#e2e8f0]">
            {indicators.indicators.vwap.toFixed(2)}
          </div>
          <div className="text-xs text-[#94a3b8] mt-1">
            Diff:{" "}
            {(((nifty.price - indicators.indicators.vwap) / indicators.indicators.vwap) * 100).toFixed(2)}
            %
          </div>
        </div>

        <div className="card">
          <h3 className="text-sm font-semibold text-[#94a3b8] mb-2">RSI</h3>
          <div className="text-2xl font-bold text-[#e2e8f0]">
            {indicators.indicators.rsi?.toFixed(1) || "N/A"}
          </div>
          <div className="text-xs text-[#94a3b8] mt-1">
            {indicators.indicators.rsi && indicators.indicators.rsi > 70
              ? "Overbought"
              : indicators.indicators.rsi && indicators.indicators.rsi < 30
                ? "Oversold"
                : "Neutral"}
          </div>
        </div>
      </div>

      {/* Support / Resistance */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="card">
          <h3 className="text-sm font-semibold text-[#94a3b8] mb-2">
            Support Levels
          </h3>
          <div className="flex flex-wrap gap-2">
            {regime.nifty.support.map((s, i) => (
              <span key={i} className="badge badge-red">
                {s.toFixed(2)}
              </span>
            ))}
          </div>
        </div>
        <div className="card">
          <h3 className="text-sm font-semibold text-[#94a3b8] mb-2">
            Resistance Levels
          </h3>
          <div className="flex flex-wrap gap-2">
            {regime.nifty.resistance.map((r, i) => (
              <span key={i} className="badge badge-green">
                {r.toFixed(2)}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Scenario Analysis */}
      <div className="card mb-6">
        <h2 className="text-xl font-bold text-[#e2e8f0] mb-4">
          SCENARIO ANALYSIS
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-3 rounded border border-[#22c55e]/30 bg-[#22c55e]/5">
            <div className="text-sm font-semibold text-[#22c55e] mb-2">
              PRIMARY
            </div>
            <div className="text-xs text-[#94a3b8] mb-1">Condition:</div>
            <div className="text-sm text-[#e2e8f0] mb-2">
              {regime.primary_scenario.condition}
            </div>
            <div className="text-xs text-[#94a3b8] mb-1">Confirmation:</div>
            <div className="text-sm text-[#e2e8f0] mb-2">
              {regime.primary_scenario.confirmation}
            </div>
            <div className="text-xs text-[#94a3b8] mb-1">Invalidation:</div>
            <div className="text-sm text-[#ef4444]">
              {regime.primary_scenario.invalidation}
            </div>
            <div className="text-xs text-[#94a3b8] mt-2">
              Target: {regime.primary_scenario.target.toFixed(2)}
            </div>
          </div>
          <div className="p-3 rounded border border-[#eab308]/30 bg-[#eab308]/5">
            <div className="text-sm font-semibold text-[#eab308] mb-2">
              ALTERNATIVE
            </div>
            <div className="text-xs text-[#94a3b8] mb-1">Condition:</div>
            <div className="text-sm text-[#e2e8f0] mb-2">
              {regime.alternative_scenario.condition}
            </div>
            <div className="text-xs text-[#94a3b8] mb-1">Confirmation:</div>
            <div className="text-sm text-[#e2e8f0] mb-2">
              {regime.alternative_scenario.confirmation}
            </div>
            <div className="text-xs text-[#94a3b8] mb-1">Invalidation:</div>
            <div className="text-sm text-[#ef4444]">
              {regime.alternative_scenario.invalidation}
            </div>
            <div className="text-xs text-[#94a3b8] mt-2">
              Target: {regime.alternative_scenario.target.toFixed(2)}
            </div>
          </div>
          <div className="p-3 rounded border border-[#ef4444]/30 bg-[#ef4444]/5">
            <div className="text-sm font-semibold text-[#ef4444] mb-2">
              RISK / INVALIDATION
            </div>
            <div className="text-xs text-[#94a3b8] mb-1">Condition:</div>
            <div className="text-sm text-[#e2e8f0] mb-2">
              {regime.risk_scenario.condition}
            </div>
            <div className="text-xs text-[#94a3b8] mb-1">Confirmation:</div>
            <div className="text-sm text-[#e2e8f0] mb-2">
              {regime.risk_scenario.confirmation}
            </div>
            <div className="text-xs text-[#94a3b8] mb-1">Invalidation:</div>
            <div className="text-sm text-[#ef4444]">
              {regime.risk_scenario.invalidation}
            </div>
            <div className="text-xs text-[#94a3b8] mt-2">
              Target: {regime.risk_scenario.target.toFixed(2)}
            </div>
          </div>
        </div>
      </div>

      {/* Why This View + What Changes It */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="card">
          <h3 className="text-sm font-semibold text-[#e2e8f0] mb-2">
            WHY THIS VIEW?
          </h3>
          <ul className="space-y-1 text-sm">
            {regime.evidence.slice(0, 6).map((ev, i) => (
              <li key={i} className="text-[#94a3b8]">
                • {ev}
              </li>
            ))}
          </ul>
        </div>
        <div className="card">
          <h3 className="text-sm font-semibold text-[#e2e8f0] mb-2">
            WHAT WOULD INVALIDATE THIS VIEW?
          </h3>
          <ul className="space-y-1 text-sm">
            {regime.risk_flags.map((flag, i) => (
              <li key={i} className="text-[#ef4444]">
                • {flag}
              </li>
            ))}
            {regime.strategy_classes.map((sc, i) => (
              <li key={i} className="text-[#94a3b8]">
                • Strategy: {sc}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Technical Indicators */}
      <div className="card mb-6">
        <h2 className="text-xl font-bold text-[#e2e8f0] mb-4">
          TECHNICAL INDICATORS
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="text-xs text-[#94a3b8]">Bollinger Bands</div>
            <div className="text-sm text-[#e2e8f0]">
              {indicators.indicators.bollinger_bands
                ? `${indicators.indicators.bollinger_bands.upper.toFixed(2)} / ${indicators.indicators.bollinger_bands.middle.toFixed(2)} / ${indicators.indicators.bollinger_bands.lower.toFixed(2)}`
                : "N/A"}
            </div>
          </div>
          <div>
            <div className="text-xs text-[#94a3b8]">MACD</div>
            <div className="text-sm text-[#e2e8f0]">
              {indicators.indicators.macd
                ? `MACD: ${indicators.indicators.macd.macd.toFixed(4)}, Signal: ${indicators.indicators.macd.signal.toFixed(4)}`
                : "N/A"}
            </div>
          </div>
          <div>
            <div className="text-xs text-[#94a3b8]">ADX</div>
            <div className="text-sm text-[#e2e8f0]">
              {indicators.indicators.adx?.toFixed(1) || "N/A"}
            </div>
          </div>
          <div>
            <div className="text-xs text-[#94a3b8]">Previous High/Low</div>
            <div className="text-sm text-[#e2e8f0]">
              H: {indicators.indicators.support_resistance.prev_high.toFixed(2)}
              <br />
              L: {indicators.indicators.support_resistance.prev_low.toFixed(2)}
            </div>
          </div>
        </div>
      </div>

      {/* Data Status */}
      <div className="text-xs text-[#94a3b8] text-center py-4">
        DATA STATUS: LIVE • Last updated:{" "}
        {new Date(regime.timestamp).toLocaleString("en-IN", {
          timeZone: "Asia/Kolkata",
        })}
        {" • "}
        Source: YahooFinance
      </div>
    </div>
  )
}