interface Props {
  title: string;
  subtitle?: string;
  badge?: string;
  badgeColor?: string;
  children: React.ReactNode;
}

export function SectionHeader({ title, subtitle, badge, badgeColor = "bg-[#3b82f6] text-white" }: Props) {
  return (
    <div className="section-header">
      <div>
        <h2 className="section-title">{title}</h2>
        {subtitle && <p className="text-sm text-[#64748b] mt-1">{subtitle}</p>}
      </div>
      {badge && (
        <span className={`section-badge ${badgeColor}`}>{badge}</span>
      )}
    </div>
  );
}