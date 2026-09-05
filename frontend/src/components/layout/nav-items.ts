import {
  Briefcase,
  ClipboardCheck,
  Cog,
  FileBarChart,
  FileText,
  Gauge,
  KanbanSquare,
  LayoutDashboard,
  Package,
  Receipt,
  Repeat,
  ShieldCheck,
  Tags,
  Truck,
  User,
  Users,
  Warehouse,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  title: string;
  icon: LucideIcon;
  /** Present for leaf links. Groups (with `children`) omit this and just toggle. */
  href?: string;
  /** When set, the item is shown only if the user holds every listed permission. */
  permissions?: string[];
  /** Present for expandable groups. */
  children?: NavItem[];
  /**
   * Set on a not-yet-built screen. Renders disabled with a "coming in phase N"
   * tooltip in dev, and is hidden entirely in production — keeps the shell
   * honest while still letting the nav tree be demoed early.
   */
  comingInPhase?: 2 | 3;
}

export const navItems: NavItem[] = [
  {
    title: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    title: "Workspace",
    icon: Briefcase,
    children: [
      {
        title: "Quotations",
        href: "/workspace/quotations",
        icon: FileText,
        permissions: ["quotations:read"],
      },
      {
        title: "Pipeline",
        href: "/workspace/pipeline",
        icon: KanbanSquare,
        permissions: ["quotations:read"],
      },
    ],
  },
  {
    // No permission gate here — a user might hold `approvals:l1`,
    // `approvals:l2`, both or neither; the page itself shows only the levels
    // the signed-in user can act on (see `(dashboard)/approvals/page.tsx`).
    title: "Approvals",
    href: "/approvals",
    icon: ClipboardCheck,
  },
  {
    title: "Deal Health",
    href: "/dashboard/deal-health",
    icon: Gauge,
    permissions: ["dashboard:read"],
  },
  {
    title: "Reports",
    href: "/reports",
    icon: FileBarChart,
    permissions: ["reports:read"],
  },
  {
    title: "Configuration",
    icon: Cog,
    children: [
      {
        title: "Products",
        href: "/config/products",
        icon: Package,
        permissions: ["catalog:read"],
      },
      {
        title: "Price Lists",
        href: "/config/price-lists",
        icon: Tags,
        permissions: ["pricing:read"],
      },
      {
        title: "Discount Policy",
        href: "/config/policy",
        icon: ShieldCheck,
        permissions: ["policies:read"],
      },
      {
        title: "Warehouses",
        href: "/config/warehouses",
        icon: Warehouse,
        permissions: ["warehouses:read"],
      },
      {
        title: "Subscription Plans",
        href: "/config/subscription-plans",
        icon: Repeat,
        permissions: ["subscriptions:read"],
      },
      {
        title: "Customers",
        href: "/customers",
        icon: Briefcase,
        permissions: ["customers:read"],
      },
    ],
  },
  {
    title: "User Management",
    icon: Users,
    children: [
      {
        title: "Users",
        href: "/users",
        icon: User,
        permissions: ["users:read"],
      },
      {
        title: "Roles",
        href: "/roles",
        icon: ShieldCheck,
        permissions: ["roles:read"],
      },
    ],
  },
];
