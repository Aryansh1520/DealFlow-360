"use client";

import { useQuery } from "@tanstack/react-query";

import type { BadgeProps } from "@/components/ui/badge";
import { EXPECTED_CONTRACT_VERSION } from "@/lib/config";
import { useAuth } from "@/features/auth/auth-context";
import { metaApi } from "@/features/meta/api";

export const ENUMS_KEY = ["meta", "enums"];

/** Fetched once in the app shell, before the dashboard renders. Cached forever —
 * enums and transitions don't change without a redeploy. Gated on
 * `isAuthenticated`: `/meta/enums` requires a principal, so an anonymous visitor
 * on `/login` must not fire it. */
export function useEnums() {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ENUMS_KEY,
    queryFn: metaApi.enums,
    staleTime: Infinity,
    gcTime: Infinity,
    enabled: isAuthenticated,
  });
}

/** True once `/meta/enums` has loaded and its `contract_version` disagrees with
 * the frontend's `EXPECTED_CONTRACT_VERSION` constant. Dev-only banner territory. */
export function useContractMismatch(): string | null {
  const { data } = useEnums();
  if (!data) return null;
  if (data.contract_version === EXPECTED_CONTRACT_VERSION) return null;
  return data.contract_version;
}

export function useStatusLabel(status: string | null | undefined): string {
  const { data } = useEnums();
  if (!status || !data) return status ?? "—";
  return data.labels.quote_status?.[status] ?? status;
}

export function useEnumLabel(enumName: string, value: string | null | undefined): string {
  const { data } = useEnums();
  if (!value || !data) return value ?? "—";
  return data.labels[enumName]?.[value] ?? value;
}

/** `transitions[status]` — the allowed next statuses, straight from the backend.
 * Action buttons are rendered by iterating this, never a hardcoded list. */
export function useAllowedTransitions(status: string | null | undefined): string[] {
  const { data } = useEnums();
  if (!status || !data) return [];
  return data.transitions[status] ?? [];
}

type Tone = NonNullable<BadgeProps["variant"]>;

/**
 * Status -> badge tone. The **one** local mapping allowed by
 * `FRONTEND_PHASE_1.md` Task 2 — colour is presentation, not contract data, but
 * an unrecognised status (the backend added one, we haven't shipped yet) must
 * render with a neutral fallback rather than crash.
 */
const STATUS_TONES: Record<string, Tone> = {
  draft: "outline",
  pending_l1: "info",
  pending_l2: "info",
  approved: "positive",
  sent: "info",
  under_negotiation: "warning",
  confirmed: "positive",
  fulfilling: "info",
  invoiced: "info",
  paid: "positive",
  rejected: "danger",
  returned_for_revision: "warning",
  cancelled: "danger",
  expired: "danger",
};

export function useStatusTone(status: string | null | undefined): Tone {
  if (!status) return "secondary";
  return STATUS_TONES[status] ?? "secondary";
}
