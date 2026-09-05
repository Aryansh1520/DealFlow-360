"use client";

import * as React from "react";
import { Minus, Plus, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { BpsInput } from "@/components/ui/bps-input";
import { Button } from "@/components/ui/button";
import { Bps, Money } from "@/components/ui/money";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { DecisionTrace, QuoteLineRead } from "@/lib/api/types";

const COMMIT_DEBOUNCE_MS = 600;

interface LineTableProps {
  lines: QuoteLineRead[];
  currency: string;
  /** Live preview trace, positionally matched to `lines` — used only for the
   * ceiling/overage warning tooltip so it updates before the discount edit
   * commits. Money figures always come from the persisted `lines` themselves. */
  previewTrace: DecisionTrace | null;
  editable: boolean;
  onQuantityChange: (lineId: number, quantity: number) => void;
  onDiscountCommit: (lineId: number, discountBps: number) => void;
  onRemove: (lineId: number) => void;
}

export const LineTable = React.memo(function LineTable({
  lines,
  currency,
  previewTrace,
  editable,
  onQuantityChange,
  onDiscountCommit,
  onRemove,
}: LineTableProps) {
  if (lines.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
        Add a product from the catalogue to start this quote.
      </div>
    );
  }

  return (
    <TooltipProvider>
      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Product</TableHead>
              <TableHead className="w-28 text-center">Qty</TableHead>
              <TableHead className="w-32 text-right">Discount</TableHead>
              <TableHead className="text-right">Unit price</TableHead>
              <TableHead className="text-right">Net</TableHead>
              <TableHead className="text-right">Margin</TableHead>
              {editable && <TableHead className="w-10" />}
            </TableRow>
          </TableHeader>
          <TableBody>
            {lines.map((line, index) => (
              <LineRow
                key={line.id}
                line={line}
                currency={currency}
                traceLine={previewTrace?.lines[index] ?? null}
                editable={editable}
                onQuantityChange={onQuantityChange}
                onDiscountCommit={onDiscountCommit}
                onRemove={onRemove}
              />
            ))}
          </TableBody>
        </Table>
      </div>
    </TooltipProvider>
  );
});

interface LineRowProps {
  line: QuoteLineRead;
  currency: string;
  traceLine: DecisionTrace["lines"][number] | null;
  editable: boolean;
  onQuantityChange: (lineId: number, quantity: number) => void;
  onDiscountCommit: (lineId: number, discountBps: number) => void;
  onRemove: (lineId: number) => void;
}

const LineRow = React.memo(function LineRow({
  line,
  currency,
  traceLine,
  editable,
  onQuantityChange,
  onDiscountCommit,
  onRemove,
}: LineRowProps) {
  const [discountBps, setDiscountBps] = React.useState(line.discount_bps);
  const commitTimer = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  React.useEffect(() => setDiscountBps(line.discount_bps), [line.discount_bps]);

  React.useEffect(() => () => {
    if (commitTimer.current) clearTimeout(commitTimer.current);
  }, []);

  const handleDiscountChange = (bps: number) => {
    setDiscountBps(bps);
    if (commitTimer.current) clearTimeout(commitTimer.current);
    commitTimer.current = setTimeout(() => onDiscountCommit(line.id, bps), COMMIT_DEBOUNCE_MS);
  };

  const overageBps = traceLine?.overage_bps ?? line.overage_bps;
  const ceilingBps = traceLine?.effective_ceiling_bps ?? line.ceiling_bps;
  const marginBps = traceLine?.margin_bps ?? line.margin_bps;
  const rowTone = overageBps > 0 ? "bg-warning/10" : "";

  return (
    <TableRow className={rowTone}>
      <TableCell>
        <p className="font-medium">{line.product_name}</p>
        {line.added_from_suggestion && (
          <Badge variant="info" className="mt-0.5 px-1.5 py-0 text-[10px]">
            Added from suggestion
          </Badge>
        )}
      </TableCell>
      <TableCell>
        <div className="flex items-center justify-center gap-1">
          <Button
            variant="outline"
            size="icon"
            className="h-7 w-7"
            disabled={!editable || line.quantity <= 1}
            onClick={() => onQuantityChange(line.id, line.quantity - 1)}
          >
            <Minus className="h-3 w-3" />
          </Button>
          <span className="w-6 text-center text-sm tabular-nums">{line.quantity}</span>
          <Button
            variant="outline"
            size="icon"
            className="h-7 w-7"
            disabled={!editable}
            onClick={() => onQuantityChange(line.id, line.quantity + 1)}
          >
            <Plus className="h-3 w-3" />
          </Button>
        </div>
      </TableCell>
      <TableCell>
        {overageBps > 0 ? (
          <Tooltip delayDuration={150}>
            <TooltipTrigger asChild>
              <div>
                <BpsInput
                  value={discountBps}
                  onChange={handleDiscountChange}
                  disabled={!editable}
                  className="ml-auto w-24 border-warning text-warning"
                />
              </div>
            </TooltipTrigger>
            <TooltipContent>
              {(overageBps / 100).toFixed(1)} points over the {(ceilingBps / 100).toFixed(1)}% ceiling
            </TooltipContent>
          </Tooltip>
        ) : (
          <BpsInput
            value={discountBps}
            onChange={handleDiscountChange}
            disabled={!editable}
            className="ml-auto w-24"
          />
        )}
      </TableCell>
      <TableCell className="text-right">
        <Money minor={line.unit_price_minor} currency={currency} />
      </TableCell>
      <TableCell className="text-right font-medium">
        <Money minor={line.net_minor} currency={currency} />
      </TableCell>
      <TableCell className="text-right">
        <span className={cn(marginBps < 0 && "font-semibold text-danger")}>
          <Bps value={marginBps} />
        </span>
      </TableCell>
      {editable && (
        <TableCell>
          <Button variant="ghost" size="icon" onClick={() => onRemove(line.id)}>
            <Trash2 className="h-4 w-4 text-destructive" />
          </Button>
        </TableCell>
      )}
    </TableRow>
  );
});
