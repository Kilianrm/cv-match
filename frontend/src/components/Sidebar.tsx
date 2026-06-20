"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Briefcase, Zap, User, LayoutDashboard, Bell } from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();
  const unreadNotifications = 1;

  const isActive = (path: string) => pathname === path;

  const links = [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/profile", label: "Profile", icon: User },
    { href: "/matches", label: "Job Matches", icon: Briefcase },
    { href: "/optimization", label: "Optimize CV", icon: Zap },
    { href: "/notifications", label: "Notifications", icon: Bell },
  ];

  return (
    <aside className="sticky top-0 flex h-screen w-72 flex-col border-r border-primary/15 bg-foreground text-background">
      <div className="border-b border-primary/15 px-6 py-6">
        <h1 className="text-2xl font-bold tracking-tight">CV Match</h1>
        <p className="mt-1 text-sm text-background/65">Job Matching Platform</p>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-4 py-5">
        {links.map(({ href, label, icon: Icon }) => (
          <Link key={href} href={href}>
            <div
              className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors ${
                isActive(href)
                  ? "bg-primary text-white"
                  : "text-background/70 hover:bg-white/8 hover:text-white"
              }`}
            >
              <Icon size={18} />
              <span>{label}</span>
              {href === "/notifications" && unreadNotifications > 0 ? (
                <span className="ml-auto inline-flex min-w-5 items-center justify-center rounded-full bg-accent px-1.5 py-0.5 text-[10px] font-semibold leading-none text-white">
                  {unreadNotifications > 99 ? "99+" : unreadNotifications}
                </span>
              ) : null}
            </div>
          </Link>
        ))}
      </nav>

      <div className="border-t border-primary/15 p-4">
        <div className="mb-3 rounded-lg bg-white/5 px-3 py-2 text-xs text-background/65">
          Signed in session
        </div>
        <a href="/api/auth/logout">
          <button className="w-full rounded-lg border border-white/20 px-4 py-2 text-sm font-medium text-background/90 transition hover:bg-white/10 hover:text-white">
            Logout
          </button>
        </a>
      </div>
    </aside>
  );
}
