"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/demo", label: "Demo" },
] as const;

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-56 shrink-0 sticky top-0 h-screen flex flex-col bg-surface border-r border-border overflow-y-auto">
      {/* Brand */}
      <div className="px-6 pt-8 pb-6 border-b border-border">
        <p className="text-2xl font-bold text-foreground font-serif leading-none tracking-tight">
          BosesPH
        </p>
        <p className="text-xs text-muted-foreground font-sans mt-2 leading-relaxed">
          Kapampangan ASR
        </p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {links.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={`flex items-center w-full px-3 py-2 rounded-lg text-sm font-sans transition-all duration-150 ${
              pathname === href
                ? "bg-foreground text-background font-semibold"
                : "text-muted-foreground hover:text-foreground hover:bg-muted"
            }`}
          >
            {label}
          </Link>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-6 py-5 border-t border-border">
        <p className="text-[11px] text-muted-foreground/40 font-sans leading-relaxed">
          Philippine Languages Database
          <br />
          Whisper fine-tuning pipeline
        </p>
      </div>
    </aside>
  );
}
