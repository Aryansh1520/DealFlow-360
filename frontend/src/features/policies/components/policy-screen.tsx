"use client";

import * as React from "react";
import { Pencil } from "lucide-react";

import { getErrorMessage } from "@/lib/api-client";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/features/auth/auth-context";
import type { PolicyRead } from "@/lib/api/types";
import { ActivatePolicyDialog } from "@/features/policies/components/activate-policy-dialog";
import { PolicyForm } from "@/features/policies/components/policy-form";
import { PolicyView } from "@/features/policies/components/policy-view";
import { usePolicies } from "@/features/policies/hooks";

export function PolicyScreen() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("policies:write");

  const { data, isLoading, isError, error } = usePolicies();
  const [selectedVersion, setSelectedVersion] = React.useState<number | null>(null);
  const [isEditing, setIsEditing] = React.useState(false);
  const [activating, setActivating] = React.useState<PolicyRead | null>(null);

  const versions = React.useMemo(
    () => [...(data?.items ?? [])].sort((a, b) => b.version - a.version),
    [data]
  );

  React.useEffect(() => {
    if (selectedVersion == null && versions.length > 0) {
      setSelectedVersion(versions.find((v) => v.is_active)?.version ?? versions[0].version);
    }
  }, [versions, selectedVersion]);

  const selected = versions.find((v) => v.version === selectedVersion) ?? null;

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Failed to load discount policy</AlertTitle>
        <AlertDescription>{getErrorMessage(error)}</AlertDescription>
      </Alert>
    );
  }

  if (isLoading || !selected) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-card p-4 shadow-sm">
        <div className="flex items-center gap-3">
          <Select
            value={String(selected.version)}
            onValueChange={(value) => {
              setSelectedVersion(Number(value));
              setIsEditing(false);
            }}
          >
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {versions.map((version) => (
                <SelectItem key={version.id} value={String(version.version)}>
                  Version {version.version}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {selected.is_active ? (
            <Badge variant="positive">Active</Badge>
          ) : (
            <Badge variant="outline">Draft</Badge>
          )}
        </div>
        {canWrite && !isEditing && (
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setIsEditing(true)}>
              <Pencil />
              Edit as new draft
            </Button>
            {!selected.is_active && (
              <Button onClick={() => setActivating(selected)}>Activate this version</Button>
            )}
          </div>
        )}
      </div>

      {isEditing ? (
        <PolicyForm
          source={selected}
          onCreated={(created) => {
            setSelectedVersion(created.version);
            setIsEditing(false);
          }}
          onCancel={() => setIsEditing(false)}
        />
      ) : (
        <PolicyView policy={selected} />
      )}

      <ActivatePolicyDialog policy={activating} onClose={() => setActivating(null)} />
    </div>
  );
}
