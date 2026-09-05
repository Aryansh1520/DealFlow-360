"use client";

import * as React from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { getErrorMessage } from "@/lib/api-client";
import type { PreviewLine } from "@/lib/api/types";
import { quotationsApi } from "@/features/quotations/api";

export interface EditorLine {
  /** Stable React key — survives across preview cycles even before the line
   * has a server-assigned id. */
  key: string;
  lineId: number | null;
  productId: number;
  productName: string;
  variantId: number | null;
  quantity: number;
  discountBps: number;
}

export interface EditorState {
  lines: EditorLine[];
  orderDiscountBps: number;
}

function hashEditorState(state: EditorState): string {
  return JSON.stringify([
    state.orderDiscountBps,
    state.lines.map((l) => [l.productId, l.variantId, l.quantity, l.discountBps]),
  ]);
}

const DEBOUNCE_MS = 250;

/**
 * `FRONTEND_PHASE_2.md` Task 2b — debounces `editorState` by 250ms, aborts
 * superseded requests, and never blanks the totals mid-type
 * (`placeholderData: keepPreviousData`). `isStale` tells the caller the
 * on-screen numbers are behind the latest keystroke, so a submit/confirm
 * button can disable itself rather than act on stale totals.
 */
export function useQuotePreview(quotationId: number, editorState: EditorState) {
  const [debounced, setDebounced] = React.useState(editorState);
  const editorRef = React.useRef(editorState);
  editorRef.current = editorState;

  React.useEffect(() => {
    const timer = setTimeout(() => setDebounced(editorRef.current), DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [editorState]);

  const hash = hashEditorState(debounced);

  const query = useQuery({
    queryKey: ["quote", quotationId, "preview", hash],
    queryFn: ({ signal }) => {
      const lines: PreviewLine[] = debounced.lines.map((l) => ({
        product_id: l.productId,
        variant_id: l.variantId,
        quantity: l.quantity,
        discount_bps: l.discountBps,
      }));
      return quotationsApi.preview(
        quotationId,
        { lines, order_discount_bps: debounced.orderDiscountBps },
        signal
      );
    },
    enabled: debounced.lines.length > 0,
    placeholderData: keepPreviousData,
    retry: false,
  });

  const isStale = hashEditorState(editorState) !== hash;

  return {
    computation: query.data ?? null,
    isStale: isStale || query.isFetching,
    isFetching: query.isFetching,
    error: query.error ? getErrorMessage(query.error) : null,
  };
}
