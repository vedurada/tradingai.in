import { Metadata } from "next";
export const metadata: Metadata = { title: "AI — TradingAI" };

export default function AIPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">AI Intelligence</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="section-title">AI Market View</h2>
          <div className="mt-4">
            <div className="text-6xl font-bold text-[#22c55e]">BULLISH</div>
            <p className="text-[#94a3b8] mt-2">Confidence: 74%</p>
          </div>
          <div className="mt-6 space-y-3">
            <h3 className="font-semibold text-[#22c55e]">Why Bullish</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start gap-2">
                <span className="text-[#22c55e]">✓</span>
                <span className="text-[#94a3b8]">Price above VWAP</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[#22c55e]">✓</span>
                <span className="text-[#94a3b8]">EMA20 above EMA50</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[#22c55e]">✓</span>
                <span className="text-[#94a3b8]">Positive market breadth</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[#22c55e]">✓</span>
                <span className="text-[#94a3b8]">Put OI support at 25,000</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[#22c55e]">✓</span>
                <span className="text-[#94a3b8]">VIX declining</span>
              </li>
            </ul>
          </div>
        </div>
        <div className="card">
          <h2 className="section-title">Key Risks</h2>
          <div className="mt-4 space-y-3">
            <div className="flex items-start gap-2">
              <span className="text-[#f59e0b]">⚠</span>
              <span className="text-[#94a3b8] text-sm">Resistance at 25,300</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-[#f59e0b]">⚠</span>
              <span className="text-[#94a3b8] text-sm">Bank NIFTY momentum weakening</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-[#f59e0b]">⚠</span>
              <span className="text-[#94a3b8] text-sm">Global volatility uncertainty</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}