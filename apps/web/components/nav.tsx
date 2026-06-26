"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/demo", label: "Demo" },
] as const;

export default function Nav() {
  const pathname = usePathname();
  return (
    <nav className="sticky top-0 z-40 flex items-center justify-between h-16 px-6 bg-surface/80 backdrop-blur-md border-b border-border">
      <div className="flex items-baseline gap-2.5">
        <span className="font-bold text-xl text-foreground font-serif leading-none">BosesPH</span>
        <span className="hidden sm:inline text-xs text-muted-foreground/60 font-sans tracking-wide">
          Kapampangan ASR
        </span>
      </div>
      <div className="flex items-center gap-1">
        {links.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={`px-3 py-1.5 rounded-md text-sm font-sans transition-all duration-150 ${
              pathname === href
                ? "bg-foreground text-background font-medium"
                : "text-muted-foreground hover:text-foreground hover:bg-muted"
            }`}
          >
            {label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
