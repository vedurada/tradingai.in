import { Sidebar } from "@/components/common/Sidebar";
import { Header } from "@/components/common/Header";
import { MarketTicker } from "@/components/market/MarketTicker";
import "@/styles/globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "TradingAI — Financial Market Intelligence",
  description: "AI-powered market intelligence for Indian and global markets",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#060d1b] text-[#e2e8f0]">
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <div className="flex-1 flex flex-col overflow-hidden">
            <Header />
            <MarketTicker />
            <main className="flex-1 overflow-auto p-6">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}