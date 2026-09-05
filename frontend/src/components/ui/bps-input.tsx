"use client";

import * as React from "react";

import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";

interface BpsInputProps
  extends Omit<React.ComponentProps<"input">, "value" | "onChange" | "type"> {
  /** Basis points — the wire value (1250 == 12.5%). */
  value: number;
  /** Emits basis points. */
  onChange: (bps: number) => void;
}

/**
 * A human-facing percentage that emits/accepts basis points. Every discount,
 * ceiling and tax field in a form uses this — `FRONTEND_PHASE_1.md` Task 7.
 */
export const BpsInput = React.forwardRef<HTMLInputElement, BpsInputProps>(
  ({ value, onChange, className, ...props }, ref) => {
    const [text, setText] = React.useState(() => (value / 100).toString());
    const focused = React.useRef(false);

    React.useEffect(() => {
      if (!focused.current) setText((value / 100).toString());
    }, [value]);

    return (
      <div className="relative">
        <Input
          ref={ref}
          inputMode="decimal"
          className={cn("pr-8 text-right tabular-nums", className)}
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
            setText(parsed.toString());
            onChange(Math.round(parsed * 100));
          }}
          {...props}
        />
        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
          %
        </span>
      </div>
    );
  }
);
BpsInput.displayName = "BpsInput";
