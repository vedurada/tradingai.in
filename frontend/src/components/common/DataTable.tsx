import { LoadingState } from "./LoadingState";
import { ErrorState } from "./LoadingState";
import { EmptyState } from "./LoadingState";

interface Props {
  columns: string[];
  data: Record<string, any>[];
  loading?: boolean;
  error?: string;
}

export function DataTable({ columns, data, loading, error }: Props) {
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!data || data.length === 0) return <EmptyState message="No data available" />;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#1a2d4d]">
            {columns.map((col) => (
              <th key={col} className="px-4 py-3 text-left text-[#94a3b8] font-semibold">{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} className="border-b border-[#0d1931] hover:bg-[#0d1931]">
              {columns.map((col) => (
                <td key={col} className="px-4 py-3">{row[col] ?? "-"}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}