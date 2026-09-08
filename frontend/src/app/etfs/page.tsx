import { Metadata } from "next";
export const metadata: Metadata = { title: "ETFs — TradingAI" };

export default function ETFsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">ETFs & Funds</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[
          { name: "Nifty BeES", price: "1,842.00", change: "+5.20" },
          { name: "Gold ETF", price: "72.45", change: "-0.35" },
          { name: "Nifty Bank ETF", price: "412.00", change: "+3.10" },
        ].map((etf) => (
          <div key={etf.name} className="card">
            <h2 className="section-title">{etf.name}</h2>
            <div className="text-3xl font-bold">{etf.price}</div>
            <div className={`font-semibold ${parseFloat(etf.change) >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>
              {etf.change}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}