"use client";

import { useEffect, useState } from "react";

export default function NewsPage() {
  const [articles, setArticles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await fetch("/api/v1/news");
        if (!res.ok) throw new Error("Failed");
        const data = await res.json();
        setArticles(data.articles || []);
      } catch {
        // keep stale
      } finally {
        setLoading(false);
      }
    }
    fetchData();
    const interval = setInterval(fetchData, 300000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="p-6 text-[#94a3b8]">Loading news...</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">News</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {articles.map((article, i) => (
          <div key={i} className="card">
            <div className="flex justify-between items-start">
              <h3 className="font-semibold">{article.title}</h3>
              <span className="text-xs text-[#64748b]">{article.source || ""}</span>
            </div>
            <div className="mt-2 flex gap-2 items-center">
              <span className={`text-xs px-2 py-1 rounded ${article.sentiment === "positive" ? "bg-green-900/50 text-green-400" : article.sentiment === "negative" ? "bg-red-900/50 text-red-400" : "bg-gray-800 text-gray-400"}`}>
                {article.sentiment}
              </span>
              <span className="text-xs text-[#64748b]">{article.category || "market"}</span>
            </div>
            {article.summary && <p className="mt-2 text-sm text-[#94a3b8]">{article.summary}</p>}
          </div>
        ))}
        {articles.length === 0 && (
          <div className="card col-span-2 text-center text-[#64748b] py-8">No news articles available</div>
        )}
      </div>
    </div>
  );
}