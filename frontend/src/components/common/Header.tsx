"use client";
import { useState, useEffect } from "react";
import { Clock, Wifi } from "lucide-react";

export function Header() {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-14 bg-[#0a1428] border-b border-[#1a2d4d] flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        <h1 className="font-bold text-lg">TradingAI</h1>
        <div className="flex items-center gap-2 text-sm">
          <Wifi size={14} className="text-[#22c55e]" />
          <span className="text-[#22c55e]">Connected</span>
        </div>
      </div>
      <div className="flex items-center gap-4 text-sm text-[#94a3b8]">
        <div className="flex items-center gap-2">
          <Clock size={14} />
          <span>{time.toLocaleTimeString("en-IN", { hour12: false })}</span>
        </div>
        <div className="market-status-live text-xs py-1 px-3">
          LIVE
        </div>
      </div>
    </header>
  );
}