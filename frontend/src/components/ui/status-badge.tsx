import { Badge } from "@/components/ui/badge";
import { useStatusLabel, useStatusTone } from "@/features/meta/hooks";

interface StatusBadgeProps {
  status: string | null | undefined;
  className?: string;
}

/** The one component every screen uses to render a `quote_status`. Colour comes
 * from `useStatusTone`, label from `/meta/enums` — nothing here is hardcoded, so
 * a new status the backend adds renders (neutral) instead of crashing. */
export function StatusBadge({ status, className }: StatusBadgeProps) {
  const tone = useStatusTone(status);
  const label = useStatusLabel(status);
  return (
    <Badge variant={tone} className={className}>
      {label}
    </Badge>
  );
}
