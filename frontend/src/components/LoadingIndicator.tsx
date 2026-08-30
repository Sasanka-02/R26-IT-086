import { Loader2 } from "lucide-react";

interface LoadingIndicatorProps {
  message?: string;
}

export default function LoadingIndicator({
  message = "Analyzing fluency and speech features...",
}: LoadingIndicatorProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center gap-3 rounded-lg border border-brand-100 bg-brand-50 px-4 py-3 text-brand-700"
    >
      <Loader2 className="animate-spin" size={20} />
      <span className="text-sm font-medium">{message}</span>
    </div>
  );
}
