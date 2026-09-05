"use client";

import * as React from "react";
import { Loader2, Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MoneyInput } from "@/components/ui/money-input";
import { useIdempotencyKey } from "@/lib/api/idempotency";
import type { InvoiceRead, SupersedeLine } from "@/lib/api/types";
import { useSupersedeInvoice } from "@/features/billing/hooks";

/** Issues a full-reversal credit note plus a corrected invoice. The corrected
 * lines are seeded from the original so a correction is usually an edit, not a
 * rebuild. */
export function SupersedeDialog({
  quotationId,
  invoice,
  open,
  onOpenChange,
}: {
  quotationId: number;
  invoice: InvoiceRead;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [reason, setReason] = React.useState("");
  const [lines, setLines] = React.useState<SupersedeLine[]>([]);
  const [seq, setSeq] = React.useState(0);
  const idempotencyKey = useIdempotencyKey(`supersede-${invoice.id}-${seq}`);
  const supersede = useSupersedeInvoice(quotationId, invoice.id);

  React.useEffect(() => {
    if (open) {
      setReason("");
      setLines(
        invoice.lines.map((l) => ({
          description: l.description,
          quantity: l.quantity,
          unit_price_minor: l.unit_price_minor,
          tax_minor: l.tax_minor,
          amount_minor: l.amount_minor,
        }))
      );
      setSeq((n) => n + 1);
    }
  }, [open, invoice.lines]);

  const patch = (i: number, next: Partial<SupersedeLine>) =>
    setLines((ls) => ls.map((l, idx) => (idx === i ? { ...l, ...next } : l)));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            if (!reason.trim() || lines.length === 0) return;
            await supersede.mutateAsync({ payload: { reason: reason.trim(), lines }, idempotencyKey });
            onOpenChange(false);
          }}
        >
          <DialogHeader>
            <DialogTitle>Supersede {invoice.number}</DialogTitle>
            <DialogDescription>
              A credit note reverses this invoice in full, then a corrected invoice is issued.
              The original becomes read-only.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-1.5">
              <Label>Reason</Label>
              <Input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Why is this correction needed?"
              />
            </div>

            <div className="space-y-2">
              <Label>Corrected lines</Label>
              {lines.map((line, i) => (
                <div key={i} className="grid grid-cols-[1fr_4rem_1fr_1fr_auto] items-center gap-2">
                  <Input
                    value={line.description}
                    onChange={(e) => patch(i, { description: e.target.value })}
                  />
                  <Input
                    type="number"
                    min={1}
                    value={line.quantity}
                    onChange={(e) => patch(i, { quantity: Math.max(1, Number(e.target.value) || 1) })}
                  />
                  <MoneyInput
                    value={line.unit_price_minor}
                    onChange={(v) => patch(i, { unit_price_minor: v })}
                    currency={invoice.currency}
                  />
                  <MoneyInput
                    value={line.amount_minor}
                    onChange={(v) => patch(i, { amount_minor: v })}
                    currency={invoice.currency}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => setLines((ls) => ls.filter((_, idx) => idx !== i))}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() =>
                  setLines((ls) => [
                    ...ls,
                    { description: "", quantity: 1, unit_price_minor: 0, tax_minor: 0, amount_minor: 0 },
                  ])
                }
              >
                <Plus className="h-4 w-4" /> Add line
              </Button>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="destructive"
              disabled={supersede.isPending || !reason.trim() || lines.length === 0}
            >
              {supersede.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Issue credit note & corrected invoice
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
