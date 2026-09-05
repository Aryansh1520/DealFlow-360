import { LayoutDashboard, ShieldCheck, User, Users, type LucideIcon } from "lucide-react";

export interface NavItem {
  title: string;
  icon: LucideIcon;
  /** Present for leaf links. Groups (with `children`) omit this and just toggle. */
  href?: string;
  /** When set, the item is shown only if the user holds every listed permission. */
  permissions?: string[];
  /** Present for expandable groups. */
  children?: NavItem[];
}

export const navItems: NavItem[] = [
  {
    title: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
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
