"use client";

import { Sparkles, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Money } from "@/components/ui/money";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { SuggestionRead } from "@/lib/api/types";
import { useDismissSuggestion, useSuggestions } from "@/features/quotations/hooks";

interface UpsellPanelProps {
  quotationId: number;
  onAdd: (suggestion: SuggestionRead) => void;
}

export function UpsellPanel({ quotationId, onAdd }: UpsellPanelProps) {
  const { data: suggestions, isLoading } = useSuggestions(quotationId);
  const dismiss = useDismissSuggestion(quotationId);

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="flex items-center gap-1.5 text-sm font-medium">
        <Sparkles className="h-4 w-4 text-info" />
        Suggested add-ons
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={index} className="h-28 w-full" />
          ))}
        </div>
      ) : suggestions && suggestions.length > 0 ? (
        <div className="space-y-2 overflow-y-auto">
          {suggestions.map((suggestion) => (
            <div
              key={suggestion.product_id}
              className="space-y-2 rounded-lg border bg-card p-3 shadow-sm"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{suggestion.product_name}</p>
                  <p className="text-xs text-muted-foreground">
                    <Money minor={suggestion.list_price_minor} currency={suggestion.currency} />
                  </p>
                </div>
                {suggestion.is_promoted && <Badge variant="info">Promoted</Badge>}
              </div>

              <p className="text-sm font-semibold text-positive">
                +<Money minor={suggestion.margin_delta_minor} currency={suggestion.currency} /> margin
              </p>

              <p className="text-xs text-muted-foreground">{suggestion.reason}</p>

              <Badge variant="secondary" className="text-[10px]">
                {suggestion.lift.toFixed(1)}× lift · {suggestion.support_count} orders
              </Badge>

              <div className="flex gap-2 pt-1">
                <Button size="sm" className="flex-1" onClick={() => onAdd(suggestion)}>
                  Add to Quote
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => dismiss.mutate(suggestion.product_id)}
                >
                  <X className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className={cn("p-4 text-center text-sm text-muted-foreground")}>
          No suggestions yet — add a product to see what&apos;s usually bought with it.
        </p>
      )}
    </div>
  );
}
