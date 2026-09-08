import { Metadata } from "next";
export const metadata: Metadata = { title: "Markets — TradingAI" };

export default function MarketsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Markets</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="card">
          <h2 className="section-title">NIFTY 50</h2>
          <div className="text-3xl font-bold">25,142.35</div>
          <div className="text-[#22c55e]">+105.20 (+0.42%)</div>
        </div>
        <div className="card">
          <h2 className="section-title">BANKNIFTY</h2>
          <div className="text-3xl font-bold">55,230.50</div>
          <div className="text-[#22c55e]">+245.75 (+0.45%)</div>
        </div>
        <div className="card">
          <h2 className="section-title">SENSEX</h2>
          <div className="text-3xl font-bold">82,350.75</div>
          <div className="text-[#22c55e]">+312.50 (+0.38%)</div>
        </div>
      </div>
    </div>
  );
}