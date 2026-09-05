"use client";

import { Loader2 } from "lucide-react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import type { PolicyRead } from "@/lib/api/types";
import { useActivatePolicy } from "@/features/policies/hooks";

interface ActivatePolicyDialogProps {
  policy: PolicyRead | null;
  onClose: () => void;
}

/** Names the version number explicitly — activation swaps the version every
 * quote gets evaluated against, so the confirmation must not be vague. */
export function ActivatePolicyDialog({ policy, onClose }: ActivatePolicyDialogProps) {
  const activate = useActivatePolicy();

  const handleConfirm = async (event: React.MouseEvent) => {
    event.preventDefault();
    if (!policy) return;
    await activate.mutateAsync(policy.id);
    onClose();
  };

  return (
    <AlertDialog open={Boolean(policy)} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Activate policy v{policy?.version}?</AlertDialogTitle>
          <AlertDialogDescription>
            Every quotation evaluated from now on uses v{policy?.version}&apos;s ceilings,
            weights and thresholds. Quotations already evaluated keep the policy version they
            were scored under.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={handleConfirm} disabled={activate.isPending}>
            {activate.isPending && <Loader2 className="animate-spin" />}
            Activate v{policy?.version}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
