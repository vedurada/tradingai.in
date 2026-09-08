interface Props {
  title: string;
  price: string;
  change: string;
  changePct: string;
  isUp: boolean;
}

export function MarketCard({ title, price, change, changePct, isUp }: Props) {
  return (
    <div className="card">
      <h3 className="text-sm text-[#94a3b8] uppercase tracking-wider">{title}</h3>
      <div className="text-2xl font-bold mt-2">{price}</div>
      <div className={`text-sm font-semibold ${isUp ? "text-[#22c55e]" : "text-[#ef4444]"}`}>
        {change} ({changePct})
      </div>
    </div>
  );
}