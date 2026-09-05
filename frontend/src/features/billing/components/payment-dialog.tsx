"use client";

import * as React from "react";
import { Loader2 } from "lucide-react";

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
import type { InvoiceRead } from "@/lib/api/types";
import { useRecordPayment } from "@/features/billing/hooks";

export function PaymentDialog({
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
  const [amount, setAmount] = React.useState(invoice.balance_minor);
  const [method, setMethod] = React.useState("bank_transfer");
  const [reference, setReference] = React.useState("");
  const [seq, setSeq] = React.useState(0);
  const idempotencyKey = useIdempotencyKey(`payment-${invoice.id}-${seq}`);
  const record = useRecordPayment(quotationId, invoice.id);

  React.useEffect(() => {
    if (open) {
      setAmount(invoice.balance_minor);
      setSeq((n) => n + 1);
    }
  }, [open, invoice.balance_minor]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            if (amount <= 0) return;
            await record.mutateAsync({
              payload: { amount_minor: amount, method, reference: reference || null },
              idempotencyKey,
            });
            onOpenChange(false);
          }}
        >
          <DialogHeader>
            <DialogTitle>Record a payment on {invoice.number}</DialogTitle>
            <DialogDescription>
              Outstanding balance is settled when the full amount is recorded.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-1.5">
              <Label>Amount</Label>
              <MoneyInput value={amount} onChange={setAmount} currency={invoice.currency} />
            </div>
            <div className="space-y-1.5">
              <Label>Method</Label>
              <Input value={method} onChange={(e) => setMethod(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label>Reference (optional)</Label>
              <Input
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                placeholder="Transaction id…"
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={record.isPending || amount <= 0}>
              {record.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Record payment
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
