"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuth } from "@/features/auth/auth-context";

export default function PortalHomePage() {
  const { customer } = useAuth();

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold tracking-tight">My Quotations</h1>
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Welcome{customer ? `, ${customer.name}` : ""}</CardTitle>
          <CardDescription>
            Quotations sent to you by your sales rep will show up here.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">Nothing to show yet.</CardContent>
      </Card>
    </div>
  );
}
