import { ContractVersionBanner } from "@/components/layout/contract-version-banner";

/**
 * Thin wrapper for everything under `/portal`. The authenticated customer shell
 * (guard + chrome) lives in `(app)/layout.tsx` so `/portal/access/[token]` — the
 * route that mints the session in the first place — can sit outside the guard.
 */
export default function PortalRootLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-muted/30">
      <ContractVersionBanner />
      {children}
    </div>
  );
}
