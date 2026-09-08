export default function Home() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div className="card col-span-1 md:col-span-2 lg:col-span-3">
        <h1 className="text-3xl font-bold mb-2">TradingAI</h1>
        <p className="text-[#94a3b8]">Financial Market Intelligence Platform</p>
      </div>
      <div className="card">
        <h2 className="section-title">NIFTY</h2>
        <div className="text-4xl font-bold text-[#e2e8f0]">25,142.35</div>
        <div className="text-[#22c55e] font-semibold">+105.20 (+0.42%)</div>
      </div>
      <div className="card">
        <h2 className="section-title">BANKNIFTY</h2>
        <div className="text-4xl font-bold text-[#e2e8f0]">55,230.50</div>
        <div className="text-[#22c55e] font-semibold">+245.75 (+0.45%)</div>
      </div>
      <div className="card">
        <h2 className="section-title">SENSEX</h2>
        <div className="text-4xl font-bold text-[#e2e8f0]">82,350.75</div>
        <div className="text-[#22c55e] font-semibold">+312.50 (+0.38%)</div>
      </div>
      <div className="card">
        <h2 className="section-title">India VIX</h2>
        <div className="text-4xl font-bold text-[#e2e8f0]">12.85</div>
        <div className="text-[#ef4444] font-semibold">-0.15 (-1.15%)</div>
      </div>
      <div className="card">
        <h2 className="section-title">Market Status</h2>
        <div className="market-status-live mt-2">Market Open</div>
      </div>
    </div>
  );
}