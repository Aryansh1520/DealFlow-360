"use client";

import { AlertTriangle } from "lucide-react";

import { EXPECTED_CONTRACT_VERSION } from "@/lib/config";
import { useContractMismatch } from "@/features/meta/hooks";

/** Dev-only. Fires when `/meta/enums`'s `contract_version` disagrees with the
 * frontend's `EXPECTED_CONTRACT_VERSION` — someone bumped `API_CONTRACT.md`
 * without regenerating types on the other side. Has saved more hackathons than
 * any test suite (`FRONTEND_PHASE_1.md` Task 2). */
export function ContractVersionBanner() {
  const mismatch = useContractMismatch();

  if (process.env.NODE_ENV === "production" || !mismatch) return null;

  return (
    <div className="flex items-center justify-center gap-2 bg-danger px-4 py-1.5 text-center text-xs font-medium text-danger-foreground">
      <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
      Contract mismatch: frontend expects {EXPECTED_CONTRACT_VERSION}, backend serves{" "}
      {mismatch}. Run <code className="font-mono">npm run gen:api</code>.
    </div>
  );
}
