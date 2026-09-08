import { Metadata } from "next";
export const metadata: Metadata = { title: "Trading — TradingAI" };

export default function TradingPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Trading Intelligence</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="section-title">Live Signals</h2>
          <div className="mt-4 space-y-3">
            <div className="p-3 bg-[#0a1428] rounded border-l-4 border-[#22c55e]">
              <div className="flex justify-between">
                <span className="font-semibold">NIFTY Bullish</span>
                <span className="text-[#22c55e] text-sm">BUY</span>
              </div>
              <p className="text-[#94a3b8] text-sm mt-1">Confidence: 78% | EMA20 {'>'} EMA50</p>
            </div>
            <div className="p-3 bg-[#0a1428] rounded border-l-4 border-[#ef4444]">
              <div className="flex justify-between">
                <span className="font-semibold">BANKNIFTY Bearish</span>
                <span className="text-[#ef4444] text-sm">SELL</span>
              </div>
              <p className="text-[#94a3b8] text-sm mt-1">Confidence: 65% | RSI {'>'} 70</p>
            </div>
          </div>
        </div>
        <div className="card">
          <h2 className="section-title">Market Regime</h2>
          <div className="mt-4">
            <div className="text-6xl font-bold text-[#22c55e]">BULLISH</div>
            <p className="text-[#94a3b8] mt-2">Confidence: 74%</p>
          </div>
        </div>
      </div>
    </div>
  );
}