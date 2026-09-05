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
import { useIdempotencyKey } from "@/lib/api/idempotency";
import { useActOnApproval } from "@/features/approvals/hooks";

interface ApprovalActionDialogProps {
  approvalId: number;
  action: "reject" | "return_for_revision" | null;
  onOpenChange: (open: boolean) => void;
}

const COPY = {
  reject: { title: "Reject this quotation", verb: "Reject" },
  return_for_revision: { title: "Return for revision", verb: "Return" },
};

/** Reject and Return **require a reason** — enforced here, in the form, not
 * by waiting for a backend error (`FRONTEND_PHASE_2.md` Task 5). */
export function ApprovalActionDialog({ approvalId, action, onOpenChange }: ApprovalActionDialogProps) {
  const [reason, setReason] = React.useState("");
  const act = useActOnApproval(approvalId);
  // Generated once per mount, reused for every retry of this same intent —
  // contract §6. The parent remounts this component (via `key`) each time it
  // opens a fresh action, so a new key is minted per distinct button press.
  const idempotencyKey = useIdempotencyKey(`${action}-${approvalId}`);

  if (!action) return null;
  const copy = COPY[action];

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!reason.trim()) return;
    await act.mutateAsync({ action, reason: reason.trim(), idempotencyKey });
    onOpenChange(false);
  };

  return (
    <Dialog open={Boolean(action)} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>{copy.title}</DialogTitle>
            <DialogDescription>A reason is required and is visible to the rep.</DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-4">
            <Label htmlFor="reason">Reason</Label>
            <Input
              id="reason"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="e.g. Services discount too far over ceiling"
              autoFocus
            />
            {!reason.trim() && (
              <p className="text-xs text-muted-foreground">Required to continue.</p>
            )}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="destructive" disabled={!reason.trim() || act.isPending}>
              {act.isPending && <Loader2 className="animate-spin" />}
              {copy.verb}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
