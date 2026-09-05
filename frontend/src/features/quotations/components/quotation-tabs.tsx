"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import { useAuth } from "@/features/auth/auth-context";

/** Sub-navigation shared by the builder, fulfilment and billing screens for one
 * quotation. Tabs the user has no permission for are simply not shown. */
export function QuotationTabs({ quotationId }: { quotationId: number }) {
  const pathname = usePathname();
  const { hasPermission } = useAuth();
  const base = `/workspace/quotations/${quotationId}`;

  const tabs = [
    { href: base, label: "Builder", show: hasPermission("quotations:read") },
    { href: `${base}/fulfillment`, label: "Fulfilment", show: hasPermission("fulfillment:read") },
    { href: `${base}/billing`, label: "Billing", show: hasPermission("billing:read") },
  ].filter((t) => t.show);

  if (tabs.length < 2) return null;

  return (
    <nav className="mb-6 flex gap-1 border-b">
      {tabs.map((tab) => {
        const active = tab.href === base ? pathname === base : pathname.startsWith(tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={cn(
              "border-b-2 px-4 py-2 text-sm font-medium transition-colors",
              active
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
