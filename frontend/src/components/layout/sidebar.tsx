import Link from "next/link";

import { APP_NAME } from "@/lib/config";
import { NavLinks } from "@/components/layout/nav-links";

export function Sidebar() {
  return (
    <aside className="hidden w-64 shrink-0 flex-col bg-sidebar text-sidebar-foreground md:flex">
      <div className="flex h-16 items-center gap-2 border-b border-sidebar-border px-6">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-sidebar-primary text-sm font-bold text-sidebar-primary-foreground">
          {APP_NAME.charAt(0).toUpperCase()}
        </div>
        <Link href="/dashboard" className="truncate text-base font-semibold tracking-tight">
          {APP_NAME}
        </Link>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-sidebar-foreground/50">
          Menu
        </p>
        <NavLinks />
      </div>
    </aside>
  );
}
