"use client";

import { useEffect, useState } from "react";

export default function OptionsPage() {
  const [chain, setChain] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await fetch("/api/v1/market/option-chain?symbol=NIFTY");
        if (!res.ok) throw new Error("Failed");
        setChain(await res.json());
      } catch {
        // keep stale
      } finally {
        setLoading(false);
      }
    }
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="p-6 text-[#94a3b8]">Loading options...</div>;

  const calls = chain?.call_contracts || [];
  const puts = chain?.put_contracts || [];
  const underlying = chain?.underlying_price || 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Options</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="section-title">Option Chain — NIFTY</h2>
          <p className="text-[#94a3b8] mt-2">Underlying: {underlying.toFixed(2)}</p>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[#94a3b8]">
                  <th className="text-left p-2">Strike</th>
                  <th className="text-right p-2">CE Last</th>
                  <th className="text-right p-2">CE OI</th>
                  <th className="text-right p-2">PE Last</th>
                  <th className="text-right p-2">PE OI</th>
                </tr>
              </thead>
              <tbody>
                {calls.slice(0, 10).map((c: any, i: number) => {
                  const p = puts[i];
                  return (
                    <tr key={i} className="border-t border-[#1a2d4d]">
                      <td className="p-2">{c.strike}</td>
                      <td className="text-right p-2 text-[#22c55e]">{c.last_price}</td>
                      <td className="text-right p-2">{c.open_interest}</td>
                      <td className="text-right p-2 text-[#ef4444]">{p?.last_price || "-"}</td>
                      <td className="text-right p-2">{p?.open_interest || "-"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
        <div className="card">
          <h2 className="section-title">PCR & Max Pain</h2>
          <div className="mt-4 space-y-3">
            <div className="flex justify-between">
              <span className="text-[#94a3b8]">OI PCR</span>
              <span className="font-semibold">
                {puts.reduce((s: number, p: any) => s + p.open_interest, 0) > 0
                  ? (calls.reduce((s: number, c: any) => s + c.open_interest, 0) / puts.reduce((s: number, p: any) => s + p.open_interest, 0)).toFixed(2)
                  : "-"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#94a3b8]">Volume PCR</span>
              <span className="font-semibold">
                {puts.reduce((s: number, p: any) => s + p.volume, 0) > 0
                  ? (calls.reduce((s: number, c: any) => s + c.volume, 0) / puts.reduce((s: number, p: any) => s + p.volume, 0)).toFixed(2)
                  : "-"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#94a3b8]">Max Pain</span>
              <span className="font-semibold">{chain?.max_pain || "Calculating..."}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}