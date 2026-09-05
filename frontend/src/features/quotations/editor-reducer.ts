import type { QuotationRead } from "@/lib/api/types";
import type { EditorLine, EditorState } from "@/features/quotations/use-preview";

type EditorAction =
  | { type: "reset"; quotation: QuotationRead }
  | { type: "set_quantity"; key: string; quantity: number }
  | { type: "set_discount"; key: string; discountBps: number }
  | { type: "set_order_discount"; discountBps: number }
  | { type: "add_line"; line: EditorLine }
  | { type: "remove_line"; key: string };

export function quotationToEditorState(quotation: QuotationRead): EditorState {
  return {
    orderDiscountBps: quotation.order_discount_bps ?? 0,
    lines: quotation.lines.map((line) => ({
      key: String(line.id),
      lineId: line.id,
      productId: line.product_id,
      productName: line.product_name,
      variantId: line.variant_id,
      quantity: line.quantity,
      discountBps: line.discount_bps,
    })),
  };
}

/** Holds the working line set while the rep edits — every action updates
 * state synchronously so typing never lags, independent of the debounced
 * preview and the separately-committed line mutations. */
export function editorReducer(state: EditorState, action: EditorAction): EditorState {
  switch (action.type) {
    case "reset":
      return quotationToEditorState(action.quotation);
    case "set_quantity":
      return {
        ...state,
        lines: state.lines.map((l) =>
          l.key === action.key ? { ...l, quantity: Math.max(1, action.quantity) } : l
        ),
      };
    case "set_discount":
      return {
        ...state,
        lines: state.lines.map((l) =>
          l.key === action.key
            ? { ...l, discountBps: Math.max(0, Math.min(10000, action.discountBps)) }
            : l
        ),
      };
    case "set_order_discount":
      return { ...state, orderDiscountBps: Math.max(0, Math.min(10000, action.discountBps)) };
    case "add_line":
      return { ...state, lines: [...state.lines, action.line] };
    case "remove_line":
      return { ...state, lines: state.lines.filter((l) => l.key !== action.key) };
    default:
      return state;
  }
}
