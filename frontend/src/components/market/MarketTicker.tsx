export function MarketTicker() {
  const items = [
    { symbol: "NIFTY", price: "25,142.35", change: "+105.20", up: true },
    { symbol: "BANKNIFTY", price: "55,230.50", change: "+245.75", up: true },
    { symbol: "SENSEX", price: "82,350.75", change: "+312.50", up: true },
    { symbol: "VIX", price: "12.85", change: "-0.15", up: false },
    { symbol: "USD/INR", price: "84.52", change: "+0.05", up: false },
    { symbol: "GOLD", price: "2,650", change: "+12.50", up: true },
    { symbol: "CRUDE", price: "$72.40", change: "-0.80", up: false },
  ];

  return (
    <div className="ticker-strip py-2 overflow-x-auto">
      <div className="flex items-center gap-6 px-4 whitespace-nowrap">
        {items.map((item) => (
          <div key={item.symbol} className="flex items-center gap-2 text-sm">
            <span className="font-semibold text-[#e2e8f0]">{item.symbol}</span>
            <span className="text-[#e2e8f0]">{item.price}</span>
            <span className={item.up ? "text-[#22c55e]" : "text-[#ef4444]"}>
              {item.change}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}