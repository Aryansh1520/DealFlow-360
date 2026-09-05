"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2, XCircle } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { tokenStorage } from "@/lib/api-client";
import { getErrorMessage } from "@/lib/api-client";
import { useAuth } from "@/features/auth/auth-context";
import { portalApi } from "@/features/portal/api";

/**
 * Redeems a magic link: exchanges the single-use token for a customer session,
 * then drops the customer straight onto their quotation. Lives outside the
 * portal auth guard — this is the route that *creates* the session.
 */
export default function PortalAccessPage() {
  const { token } = useParams<{ token: string }>();
  const router = useRouter();
  const { refreshUser } = useAuth();
  const [error, setError] = React.useState<string | null>(null);
  const ran = React.useRef(false);

  React.useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    (async () => {
      try {
        const result = await portalApi.redeem(token);
        tokenStorage.set(result);
        await refreshUser();
        router.replace(`/portal/quotations/${result.quotation_id}`);
      } catch (err) {
        setError(getErrorMessage(err));
      }
    })();
  }, [token, router, refreshUser]);

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center p-6">
      {error ? (
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertTitle>This link can&apos;t be used</AlertTitle>
          <AlertDescription className="space-y-3">
            <p>{error}</p>
            <p className="text-xs">
              Magic links are single-use and expire after 24 hours. Ask your rep to send a
              fresh one, or sign in with your portal password.
            </p>
            <Button size="sm" variant="outline" onClick={() => router.replace("/login")}>
              Go to sign in
            </Button>
          </AlertDescription>
        </Alert>
      ) : (
        <div className="flex items-center gap-3 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" />
          Opening your quotation…
        </div>
      )}
    </div>
  );
}
