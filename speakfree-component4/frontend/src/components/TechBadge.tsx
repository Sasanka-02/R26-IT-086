interface TechBadgeProps {
  label: string;
  sublabel?: string;
  status?: "live" | "designed";
}

export default function TechBadge({ label, sublabel, status = "live" }: TechBadgeProps) {
  return (
    <div className="flex items-center gap-2 rounded-full border px-3 py-1.5" style={{ borderColor: "var(--border)", background: "#fff" }}>
      <span
        className="h-2 w-2 rounded-full"
        style={{ background: status === "live" ? "#16a34a" : "#d9a441" }}
      />
      <div className="leading-tight">
        <p className="text-xs font-semibold" style={{ color: "var(--text)" }}>{label}</p>
        {sublabel && <p className="text-[10px]" style={{ color: "var(--text-soft)" }}>{sublabel}</p>}
      </div>
    </div>
  );
}