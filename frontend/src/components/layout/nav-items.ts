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
        comingInPhase: 2,
      },
      {
        title: "Pipeline",
        href: "/workspace/pipeline",
        icon: KanbanSquare,
        permissions: ["quotations:read"],
        comingInPhase: 2,
      },
    ],
  },
  {
    title: "Approvals",
    icon: ClipboardCheck,
    permissions: ["approvals:l1"],
    comingInPhase: 2,
  },
  {
    title: "Fulfilment",
    icon: Truck,
    permissions: ["fulfillment:read"],
    comingInPhase: 3,
  },
  {
    title: "Billing",
    icon: Receipt,
    permissions: ["billing:read"],
    comingInPhase: 3,
  },
  {
    title: "Deal Health",
    icon: Gauge,
    permissions: ["dashboard:read"],
    comingInPhase: 3,
  },
  {
    title: "Reports",
    icon: FileBarChart,
    permissions: ["reports:read"],
    comingInPhase: 3,
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
