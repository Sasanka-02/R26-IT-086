import { FormEvent, ReactNode, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  BarChart3,
  Bot,
  CalendarDays,
  Columns2,
  FlaskConical,
  HeartPulse,
  LayoutDashboard,
  LogOut,
  LucideIcon,
  Menu,
  Mic,
  Search,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useSession } from "../context/SessionContext";

interface NavItem {
  label: string;
  icon: LucideIcon;
  to: string;
  /** Returns true when this item is the current page. */
  match: (path: string, tab: string | null) => boolean;
}

const therapyTab = (id: string, fallback = false) => (path: string, tab: string | null) =>
  path === "/therapy" && (tab === id || (fallback && !tab));

const STUDENT_NAV: NavItem[] = [
  { label: "Dashboard", icon: LayoutDashboard, to: "/dashboard", match: (p) => p === "/dashboard" },
  { label: "Practice", icon: Mic, to: "/therapy?tab=practice", match: therapyTab("practice", true) },
  { label: "Assistant", icon: Bot, to: "/therapy?tab=assistant", match: therapyTab("assistant") },
  { label: "My Progress", icon: BarChart3, to: "/therapy?tab=progress", match: therapyTab("progress") },
  { label: "Weekly Plan", icon: CalendarDays, to: "/therapy?tab=plan", match: therapyTab("plan") },
  { label: "Privacy", icon: ShieldCheck, to: "/therapy?tab=privacy", match: therapyTab("privacy") },
];

const THERAPIST_NAV: NavItem[] = [
  {
    label: "Students",
    icon: Users,
    to: "/therapist",
    match: (p) => p === "/therapist" || p.startsWith("/therapist/students"),
  },
  {
    label: "Compare students",
    icon: Columns2,
    to: "/therapist/compare",
    match: (p) => p === "/therapist/compare",
  },
  {
    label: "Model evidence",
    icon: FlaskConical,
    to: "/therapist/evidence",
    match: (p) => p === "/therapist/evidence",
  },
];

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

function Brand({ compact }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5 px-2">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-teal-600 text-white">
        <HeartPulse size={17} />
      </div>
      {!compact && (
        <div className="leading-tight">
          <p className="font-display text-[15px] font-semibold text-ink">SpeakFree</p>
          <p className="text-[11px] text-ink-soft">Therapy Assistant</p>
        </div>
      )}
    </div>
  );
}

function NavList({
  items,
  compact,
  onNavigate,
}: {
  items: NavItem[];
  compact?: boolean;
  onNavigate: () => void;
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const { resetSession } = useSession();
  const { logout } = useAuth();
  const tab = new URLSearchParams(location.search).get("tab");

  const go = (to: string) => {
    if (to.startsWith("/therapy") && location.pathname !== "/therapy") resetSession();
    navigate(to);
    onNavigate();
  };

  const itemClass = (active: boolean) =>
    `group flex w-full items-center gap-3 rounded-xl text-sm font-medium transition ${
      compact ? "justify-center px-0 py-2.5" : "px-3.5 py-2.5"
    } ${active ? "bg-teal-600 text-white" : "text-ink-soft hover:bg-snow/[0.06] hover:text-ink"}`;

  return (
    <nav className="flex flex-1 flex-col gap-1.5">
      {items.map((item) => {
        const active = item.match(location.pathname, tab);
        const Icon = item.icon;
        return (
          <button
            key={item.label}
            onClick={() => go(item.to)}
            title={compact ? item.label : undefined}
            aria-current={active ? "page" : undefined}
            className={itemClass(active)}
          >
            <Icon size={18} strokeWidth={active ? 2.2 : 1.8} />
            {!compact && item.label}
          </button>
        );
      })}
      <div className="mt-auto pt-6">
        <button
          onClick={() => {
            logout();
            navigate("/");
          }}
          title={compact ? "Sign out" : undefined}
          className={itemClass(false)}
        >
          <LogOut size={18} strokeWidth={1.8} />
          {!compact && "Sign out"}
        </button>
      </div>
    </nav>
  );
}

export default function AppShell({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const isTherapist = user?.role === "therapist";
  const items = isTherapist ? THERAPIST_NAV : STUDENT_NAV;
  const [query, setQuery] = useState(() => new URLSearchParams(location.search).get("q") ?? "");

  useEffect(() => {
    setQuery(new URLSearchParams(location.search).get("q") ?? "");
  }, [location.search]);

  const submitSearch = (e: FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    const params = new URLSearchParams(isTherapist ? {} : { tab: "practice" });
    if (q) params.set("q", q);
    navigate(`${isTherapist ? "/therapist" : "/therapy"}?${params.toString()}`);
  };

  return (
    <div className="min-h-screen bg-shell lg:p-4">
      <div className="flex min-h-screen bg-panel lg:min-h-[calc(100vh-2rem)] lg:overflow-hidden lg:rounded-[28px] lg:border lg:border-snow/5">
        {/* Icon rail (md) / full sidebar (xl) */}
        <aside className="sticky top-0 hidden h-screen w-[84px] shrink-0 flex-col border-r border-snow/5 px-3 py-6 md:flex lg:h-[calc(100vh-2rem)] xl:w-64 xl:px-5">
          <div className="xl:hidden">
            <Brand compact />
          </div>
          <div className="hidden xl:block">
            <Brand />
          </div>
          <div className="mt-8 flex flex-1 flex-col xl:hidden">
            <NavList items={items} compact onNavigate={() => {}} />
          </div>
          <div className="mt-8 hidden flex-1 flex-col xl:flex">
            <NavList items={items} onNavigate={() => {}} />
          </div>
        </aside>

        {/* Mobile drawer */}
        {drawerOpen && (
          <div className="fixed inset-0 z-40 md:hidden">
            <button
              aria-label="Close menu"
              className="absolute inset-0 bg-black/60"
              onClick={() => setDrawerOpen(false)}
            />
            <aside className="relative flex h-full w-72 flex-col bg-panel px-5 py-6">
              <div className="flex items-center justify-between">
                <Brand />
                <button
                  onClick={() => setDrawerOpen(false)}
                  className="rounded-lg p-2 text-ink-soft hover:bg-snow/[0.06]"
                  aria-label="Close menu"
                >
                  <X size={18} />
                </button>
              </div>
              <div className="mt-8 flex flex-1 flex-col">
                <NavList items={items} onNavigate={() => setDrawerOpen(false)} />
              </div>
            </aside>
          </div>
        )}

        <div className="flex min-w-0 flex-1 flex-col lg:h-[calc(100vh-2rem)] lg:overflow-y-auto">
          <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-snow/5 bg-panel/90 px-4 py-4 backdrop-blur sm:px-6">
            <button
              onClick={() => setDrawerOpen(true)}
              className="rounded-lg p-2 text-ink-soft hover:bg-snow/[0.06] md:hidden"
              aria-label="Open menu"
            >
              <Menu size={20} />
            </button>
            <form onSubmit={submitSearch} className="relative w-full max-w-md">
              <Search
                size={16}
                className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-soft"
              />
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={isTherapist ? "Search students..." : "Search exercises..."}
                className="w-full rounded-xl border bg-white py-2.5 pl-10 pr-3 text-sm"
              />
            </form>
            <div className="ml-auto flex items-center gap-3">
              <div className="hidden text-right leading-tight sm:block">
                <p className="text-sm font-medium text-ink">{user?.name}</p>
                <p className="text-xs capitalize text-ink-soft">{user?.role}</p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-gold-400 to-teal-500 text-sm font-semibold text-shell">
                {initials(user?.name ?? "?")}
              </div>
            </div>
          </header>

          <main className="flex-1 px-4 py-6 sm:px-6">{children}</main>
        </div>
      </div>
    </div>
  );
}
