"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronDown } from "lucide-react";

import { cn } from "@/lib/utils";
import { useAuth } from "@/features/auth/auth-context";
import { navItems, type NavItem } from "@/components/layout/nav-items";

const isProduction = process.env.NODE_ENV === "production";

function isItemActive(item: NavItem, pathname: string): boolean {
  if (item.href) {
    return pathname === item.href || pathname.startsWith(`${item.href}/`);
  }
  return (item.children ?? []).some((child) => isItemActive(child, pathname));
}

/**
 * Recursively drops items the user lacks permission for, pruning groups left
 * empty. A `comingInPhase` item is dropped outright in production — it hasn't
 * shipped — but kept (disabled) in dev so the nav tree can be demoed early.
 */
function filterVisible(items: NavItem[], hasPermission: (...p: string[]) => boolean): NavItem[] {
  return items
    .filter((item) => !item.permissions || hasPermission(...item.permissions))
    .filter((item) => !isProduction || !item.comingInPhase)
    .map((item) =>
      item.children ? { ...item, children: filterVisible(item.children, hasPermission) } : item
    )
    .filter((item) => item.href || item.comingInPhase || (item.children?.length ?? 0) > 0);
}

export function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { hasPermission } = useAuth();

  const visibleItems = React.useMemo(
    () => filterVisible(navItems, hasPermission),
    [hasPermission]
  );

  return (
    <nav className="flex flex-col gap-1">
      {visibleItems.map((item) => (
        <NavEntry key={item.title} item={item} pathname={pathname} onNavigate={onNavigate} />
      ))}
    </nav>
  );
}

function NavEntry({
  item,
  pathname,
  onNavigate,
}: {
  item: NavItem;
  pathname: string;
  onNavigate?: () => void;
}) {
  const active = isItemActive(item, pathname);
  const [open, setOpen] = React.useState(active);

  // Keep a group expanded whenever navigation lands on one of its children.
  React.useEffect(() => {
    if (active) setOpen(true);
  }, [active]);

  if (item.children) {
    return (
      <div>
        <button
          type="button"
          onClick={() => setOpen((prev) => !prev)}
          aria-expanded={open}
          className={cn(
            "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
            "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
          )}
        >
          <item.icon className="h-4 w-4 shrink-0" />
          <span className="flex-1 text-left">{item.title}</span>
          <ChevronDown
            className={cn("h-4 w-4 shrink-0 transition-transform", open && "rotate-180")}
          />
        </button>
        {open && (
          <div className="mt-1 flex flex-col gap-1 border-l border-sidebar-border pl-4">
            {item.children.map((child) => (
              <NavEntry
                key={child.href ?? child.title}
                item={child}
                pathname={pathname}
                onNavigate={onNavigate}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  // Not yet built: no href, rendered disabled with a tooltip explaining why.
  if (!item.href) {
    return (
      <span
        title={item.comingInPhase ? `Coming in Phase ${item.comingInPhase}` : undefined}
        className="flex cursor-not-allowed items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-sidebar-foreground/30"
      >
        <item.icon className="h-4 w-4 shrink-0" />
        {item.title}
        {item.comingInPhase && (
          <span className="ml-auto rounded-full border border-sidebar-border px-1.5 py-0.5 text-[10px] uppercase tracking-wide">
            Phase {item.comingInPhase}
          </span>
        )}
      </span>
    );
  }

  return (
    <Link
      href={item.href}
      onClick={onNavigate}
      title={item.comingInPhase ? `Coming in Phase ${item.comingInPhase}` : undefined}
      className={cn(
        "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-sidebar-primary text-sidebar-primary-foreground shadow-sm"
          : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
      )}
    >
      <item.icon className="h-4 w-4 shrink-0" />
      {item.title}
      {item.comingInPhase && (
        <span className="ml-auto rounded-full border border-sidebar-border px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-sidebar-foreground/50">
          Phase {item.comingInPhase}
        </span>
      )}
    </Link>
  );
}
