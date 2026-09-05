import * as React from "react";

/**
 * A stable `Idempotency-Key` per user intent — generated when the dialog opens
 * or the button is first pressed, **not** inside the mutation function (which
 * re-runs on every retry). Contract §6: same key on retry, a new one only when
 * the user forms a new intent.
 *
 * `intentId` should change when the intent changes (e.g. the approval id, or a
 * counter that bumps each time the confirm dialog re-opens) so a fresh key is
 * minted per distinct action rather than reused across unrelated ones.
 */
export function useIdempotencyKey(intentId: string): string {
  const keyRef = React.useRef<{ intentId: string; key: string } | null>(null);

  if (!keyRef.current || keyRef.current.intentId !== intentId) {
    keyRef.current = { intentId, key: crypto.randomUUID() };
  }

  return keyRef.current.key;
}
