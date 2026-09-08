export function LoadingState() {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#3b82f6]"></div>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="text-center">
        <div className="text-[#ef4444] font-semibold text-lg">Error</div>
        <p className="text-[#94a3b8] text-sm mt-2">{message}</p>
      </div>
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="text-center">
        <div className="text-[#64748b] text-lg">No data</div>
        <p className="text-[#64748b] text-sm mt-2">{message}</p>
      </div>
    </div>
  );
}