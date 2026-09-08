"use client";

import { useEffect, useState } from "react";

interface TickerItem {
  symbol: string;
  price: string;
  change: string;
  up: boolean;
}

export function MarketTicker() {
  const [items, setItems] = useState<TickerItem[]>([
    { symbol: "NIFTY", price: "---", change: "---", up: true },
    { symbol: "BANKNIFTY", price: "---", change: "---", up: true },
    { symbol: "SENSEX", price: "---", change: "---", up: true },
    { symbol: "VIX", price: "---", change: "---", up: false },
    { symbol: "USD/INR", price: "---", change: "---", up: false },
    { symbol: "GOLD", price: "---", change: "---", up: true },
    { symbol: "CRUDE", price: "---", change: "---", up: false },
  ]);

  useEffect(() => {
    async function fetchTicker() {
      try {
        const res = await fetch("/api/v1/market/overview");
        if (!res.ok) return;
        const data = await res.json();
        setItems([
          { symbol: "NIFTY", price: data.nifty?.price?.toLocaleString() || "---", change: `${data.nifty?.change?.toFixed(2) || "---"} (${data.nifty?.change_pct?.toFixed(2) || "---"}%)`, up: (data.nifty?.change || 0) >= 0 },
          { symbol: "BANKNIFTY", price: data.banknifty?.price?.toLocaleString() || "---", change: `${data.banknifty?.change?.toFixed(2) || "---"} (${data.banknifty?.change_pct?.toFixed(2) || "---"}%)`, up: (data.banknifty?.change || 0) >= 0 },
          { symbol: "SENSEX", price: data.sensex?.price?.toLocaleString() || "---", change: `${data.sensex?.change?.toFixed(2) || "---"} (${data.sensex?.change_pct?.toFixed(2) || "---"}%)`, up: (data.sensex?.change || 0) >= 0 },
          { symbol: "VIX", price: data.vix?.price?.toFixed(2) || "---", change: `${data.vix?.change?.toFixed(2) || "---"} (${data.vix?.change_pct?.toFixed(2) || "---"}%)`, up: (data.vix?.change || 0) >= 0 },
          { symbol: "USD/INR", price: data.global_markets?.["USD/INR"]?.price?.toFixed(2) || "---", change: `${data.global_markets?.["USD/INR"]?.change?.toFixed(2) || "---"} (${data.global_markets?.["USD/INR"]?.change_pct?.toFixed(2) || "---"}%)`, up: (data.global_markets?.["USD/INR"]?.change || 0) >= 0 },
          { symbol: "GOLD", price: data.global_markets?.["GOLD"]?.price?.toFixed(2) || "---", change: `${data.global_markets?.["GOLD"]?.change?.toFixed(2) || "---"} (${data.global_markets?.["GOLD"]?.change_pct?.toFixed(2) || "---"}%)`, up: (data.global_markets?.["GOLD"]?.change || 0) >= 0 },
          { symbol: "CRUDE", price: data.global_markets?.["CRUDE"]?.price?.toFixed(2) || "---", change: `${data.global_markets?.["CRUDE"]?.change?.toFixed(2) || "---"} (${data.global_markets?.["CRUDE"]?.change_pct?.toFixed(2) || "---"}%)`, up: (data.global_markets?.["CRUDE"]?.change || 0) >= 0 },
        ]);
      } catch {
        // keep stale data
      }
    }
    fetchTicker();
    const interval = setInterval(fetchTicker, 30000);
    return () => clearInterval(interval);
  }, []);

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