/**
 * SiteFooter – shared footer.
 *   variant="full"    – landing page: brand + Platform / Project / Resources columns + copyright
 *   variant="compact" – auth pages and the signed-in app: resource links + copyright
 * Links point at sections of the landing page (/welcome#…); Landing scrolls to the hash.
 */
import { Link } from "react-router-dom";
import { Logo } from "./ui";

const COLUMNS: { title: string; links: { label: string; to: string }[] }[] = [
  {
    title: "Platform",
    links: [
      { label: "The Problem", to: "/welcome#problem" },
      { label: "How it Works", to: "/welcome#how" },
      { label: "Features", to: "/welcome#features" },
      { label: "Trust", to: "/welcome#trust" },
    ],
  },
  {
    title: "Project",
    links: [
      { label: "AI-Powered Research", to: "/welcome#platform" },
      { label: "Speech Therapy Assistant", to: "/welcome#features" },
      { label: "Impact", to: "/welcome#trust" },
    ],
  },
  {
    title: "Resources",
    links: [
      { label: "Privacy & Security", to: "/welcome#trust" },
      { label: "Accessibility", to: "/welcome#faq-accessibility" },
      { label: "FAQs", to: "/welcome#faq" },
    ],
  },
];

const year = new Date().getFullYear();

function Copyright() {
  return (
    <p className="text-center text-sm text-ink-soft">© {year} SpeakFree. All rights reserved.</p>
  );
}

export default function SiteFooter({ variant = "full" }: { variant?: "full" | "compact" }) {
  if (variant === "compact") {
    const resources = COLUMNS[2].links;
    return (
      <footer className="border-t border-line py-6">
        <nav aria-label="Footer" className="mb-3 flex flex-wrap justify-center gap-x-5 gap-y-1 text-sm">
          <Link to="/welcome" className="text-ink-soft hover:text-ink">Home</Link>
          {resources.map((l) => <Link key={l.label} to={l.to} className="text-ink-soft hover:text-ink">{l.label}</Link>)}
        </nav>
        <Copyright />
      </footer>
    );
  }

  return (
    <footer className="border-t border-line bg-white/60">
      <div className="mx-auto max-w-6xl px-4 pt-12 sm:px-6">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-[1.3fr_1fr_1fr_1fr]">
          <div>
            <Link to="/welcome" aria-label="SpeakFree home"><Logo subtitle={false} /></Link>
            <p className="mt-4 max-w-xs text-[15px] leading-relaxed text-ink-soft">AI-Based Speech Disorder Screening &amp; Therapy Assistant.</p>
          </div>
          {COLUMNS.map((col) => (
            <nav key={col.title} aria-label={col.title}>
              <h2 className="text-base font-bold text-ink">{col.title}</h2>
              <ul className="mt-4 space-y-2.5 text-[15px]">
                {col.links.map((l) => (
                  <li key={l.label}><Link to={l.to} className="text-ink-soft transition hover:text-brand">{l.label}</Link></li>
                ))}
              </ul>
            </nav>
          ))}
        </div>
        <div className="mt-10 border-t border-line py-6">
          <Copyright />
        </div>
      </div>
    </footer>
  );
}
