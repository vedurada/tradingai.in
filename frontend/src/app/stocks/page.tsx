import { Metadata } from "next";
export const metadata: Metadata = { title: "Stocks — TradingAI" };

export default function StocksPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Stocks</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[
          { name: "RELIANCE", price: "2,456.80", change: "+12.45", pct: "+0.51%" },
          { name: "TCS", price: "3,890.25", change: "-8.75", pct: "-0.22%" },
          { name: "HDFCBANK", price: "1,678.50", change: "+22.30", pct: "+1.35%" },
        ].map((stock) => (
          <div key={stock.name} className="card">
            <h2 className="section-title">{stock.name}</h2>
            <div className="text-3xl font-bold">{stock.price}</div>
            <div className={`font-semibold ${parseFloat(stock.change) >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>
              {stock.change} ({stock.pct})
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}