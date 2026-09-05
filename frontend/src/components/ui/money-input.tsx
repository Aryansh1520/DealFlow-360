"use client";

import * as React from "react";

import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";

interface MoneyInputProps
  extends Omit<React.ComponentProps<"input">, "value" | "onChange" | "type"> {
  /** Minor units (paise) — the wire value. */
  value: number;
  /** Emits minor units. */
  onChange: (minor: number) => void;
  currency?: string;
}

/**
 * A human-facing decimal amount that emits/accepts minor units. Every money
 * field in a form uses this — `FRONTEND_PHASE_1.md` Task 7: "every bug in this
 * class comes from a screen that rolled its own."
 */
export const MoneyInput = React.forwardRef<HTMLInputElement, MoneyInputProps>(
  ({ value, onChange, currency = "INR", className, ...props }, ref) => {
    const [text, setText] = React.useState(() => (value / 100).toFixed(2));
    const focused = React.useRef(false);

    React.useEffect(() => {
      if (!focused.current) setText((value / 100).toFixed(2));
    }, [value]);

    return (
      <div className="relative">
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
          {currency}
        </span>
        <Input
          ref={ref}
          inputMode="decimal"
          className={cn("pl-14 text-right tabular-nums", className)}
          value={text}
          onFocus={() => {
            focused.current = true;
          }}
          onChange={(event) => {
            const raw = event.target.value;
            setText(raw);
            const parsed = Number(raw);
            if (raw !== "" && !Number.isNaN(parsed)) onChange(Math.round(parsed * 100));
          }}
          onBlur={() => {
            focused.current = false;
            const parsed = Number(text) || 0;
            setText(parsed.toFixed(2));
            onChange(Math.round(parsed * 100));
          }}
          {...props}
        />
      </div>
    );
  }
);
MoneyInput.displayName = "MoneyInput";
