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
    <nav className="flex items-center justify-between h-14 px-6 bg-surface border-b border-border">
      <span className="font-bold text-lg text-foreground font-serif">BosesPH</span>
      <div className="flex gap-6">
        {links.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={`text-foreground text-sm hover:text-accent transition-colors ${
              pathname === href ? "underline" : ""
            }`}
          >
            {label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
