import { Metadata } from "next";
export const metadata: Metadata = { title: "News — TradingAI" };

export default function NewsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">News</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {[
          { headline: "NIFTY crosses 25,100 on strong global cues", category: "Markets", time: "14:32" },
          { headline: "RBI keeps repo rate unchanged at 6.5%", category: "Economy", time: "13:45" },
          { headline: "TCS Q2 earnings beat estimates", category: "Earnings", time: "12:15" },
          { headline: "Crude oil prices surge on supply concerns", category: "Commodities", time: "11:30" },
        ].map((news, i) => (
          <div key={i} className="card">
            <div className="flex justify-between items-start">
              <h3 className="font-semibold">{news.headline}</h3>
              <span className="text-xs text-[#64748b]">{news.time}</span>
            </div>
            <div className="mt-2">
              <span className="text-xs bg-[#0d1931] px-2 py-1 rounded text-[#3b82f6]">{news.category}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}