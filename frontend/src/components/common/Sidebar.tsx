"use client";
import { useState } from "react";
import { Menu, X, Activity } from "lucide-react";

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const navItems = [
    { label: "Home", href: "/", icon: "🏠" },
    { label: "Markets", href: "/markets", icon: "📊" },
    { label: "Options", href: "/options", icon: "📈" },
    { label: "Trading", href: "/trading", icon: "⚡" },
    { label: "Stocks", href: "/stocks", icon: "🏢" },
    { label: "ETFs", href: "/etfs", icon: "📦" },
    { label: "News", href: "/news", icon: "📰" },
    { label: "AI", href: "/ai", icon: "🤖" },
  ];

  return (
    <aside
      className={`${collapsed ? "w-16" : "w-64"} bg-[#0a1428] border-r border-[#1a2d4d] transition-all duration-300 flex flex-col`}
    >
      <div className="flex items-center justify-between p-4 border-b border-[#1a2d4d]">
        {!collapsed && <span className="font-bold text-lg">TradingAI</span>}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1 rounded hover:bg-[#11203e]"
        >
          {collapsed ? <Menu size={20} /> : <X size={20} />}
        </button>
      </div>
      <nav className="flex-1 p-2 space-y-1">
        {navItems.map((item) => (
          <a
            key={item.label}
            href={item.href}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-[#94a3b8] hover:bg-[#11203e] hover:text-[#e2e8f0] transition-colors"
          >
            <span>{item.icon}</span>
            {!collapsed && <span>{item.label}</span>}
          </a>
        ))}
      </nav>
      {!collapsed && (
        <div className="p-4 border-t border-[#1a2d4d] text-xs text-[#64748b]">
          © 2026 TradingAI
        </div>
      )}
    </aside>
  );
}