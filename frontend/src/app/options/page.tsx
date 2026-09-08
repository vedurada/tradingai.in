import { Metadata } from "next";
export const metadata: Metadata = { title: "Options — TradingAI" };

export default function OptionsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Options</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="section-title">Option Chain</h2>
          <p className="text-[#94a3b8] mt-4">Select a symbol and expiry to view the option chain.</p>
          <div className="mt-4 space-y-2">
            <div className="flex justify-between p-2 bg-[#0a1428] rounded">
              <span>NIFTY</span><span className="text-[#22c55e]">CE 25,200</span>
            </div>
            <div className="flex justify-between p-2 bg-[#0a1428] rounded">
              <span>NIFTY</span><span className="text-[#ef4444]">PE 25,000</span>
            </div>
          </div>
        </div>
        <div className="card">
          <h2 className="section-title">PCR & Max Pain</h2>
          <div className="mt-4 space-y-3">
            <div className="flex justify-between">
              <span className="text-[#94a3b8]">OI PCR</span><span className="font-semibold">1.12</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#94a3b8]">Volume PCR</span><span className="font-semibold">0.89</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#94a3b8]">Max Pain</span><span className="font-semibold">25,100</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}