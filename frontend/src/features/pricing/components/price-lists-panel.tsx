"use client";

import * as React from "react";
import { MoreHorizontal, Plus, Star } from "lucide-react";

import { getErrorMessage } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDeleteDialog } from "@/components/ui/confirm-delete-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Bps, Money } from "@/components/ui/money";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuth } from "@/features/auth/auth-context";
import type { PriceListEntryRead, PriceListRead } from "@/lib/api/types";
import { useAllProducts } from "@/features/catalog/hooks";
import { EntryFormDialog } from "@/features/pricing/components/entry-form-dialog";
import { PriceListFormDialog } from "@/features/pricing/components/price-list-form-dialog";
import {
  useDeletePriceList,
  useDeletePriceListEntry,
  usePriceListEntries,
  usePriceLists,
} from "@/features/pricing/hooks";

export function PriceListsPanel() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("pricing:write");

  const { data, isLoading, isError, error } = usePriceLists({ page: 1, page_size: 100 });
  const deletePriceList = useDeletePriceList();

  const [selectedId, setSelectedId] = React.useState<number | null>(null);
  const [formOpen, setFormOpen] = React.useState(false);
  const [editingList, setEditingList] = React.useState<PriceListRead | null>(null);
  const [deletingList, setDeletingList] = React.useState<PriceListRead | null>(null);

  React.useEffect(() => {
    if (!selectedId && data && data.items.length > 0) {
      setSelectedId(data.items[0].id);
    }
  }, [data, selectedId]);

  const selected = data?.items.find((list) => list.id === selectedId) ?? null;

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Failed to load price lists</AlertTitle>
        <AlertDescription>{getErrorMessage(error)}</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-muted-foreground">Price lists</p>
          {canWrite && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setEditingList(null);
                setFormOpen(true);
              }}
            >
              <Plus />
              New
            </Button>
          )}
        </div>
        <div className="space-y-1 rounded-lg border bg-card p-1.5 shadow-sm">
          {isLoading ? (
            Array.from({ length: 3 }).map((_, index) => (
              <Skeleton key={index} className="h-14 w-full" />
            ))
          ) : data && data.items.length > 0 ? (
            data.items.map((list) => (
              <button
                key={list.id}
                type="button"
                onClick={() => setSelectedId(list.id)}
                className={cn(
                  "flex w-full flex-col gap-1 rounded-md p-2.5 text-left transition-colors",
                  selectedId === list.id ? "bg-accent" : "hover:bg-accent/50"
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-sm font-medium">
                    {list.is_default && <Star className="h-3.5 w-3.5 text-warning" />}
                    {list.name}
                  </span>
                  {canWrite && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                        <Button variant="ghost" size="icon" className="h-6 w-6">
                          <MoreHorizontal className="h-3.5 w-3.5" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={() => {
                            setEditingList(list);
                            setFormOpen(true);
                          }}
                        >
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          className="text-destructive focus:text-destructive"
                          onClick={() => setDeletingList(list)}
                        >
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                </div>
                <div className="flex items-center gap-1.5">
                  <Badge variant="outline" className="capitalize">
                    {list.tier ?? "Any tier"}
                  </Badge>
                  <span className="text-xs text-muted-foreground">{list.currency}</span>
                </div>
              </button>
            ))
          ) : (
            <p className="p-4 text-center text-sm text-muted-foreground">No price lists yet.</p>
          )}
        </div>
      </div>

      <div>
        {selected ? (
          <EntriesTable priceList={selected} canWrite={canWrite} />
        ) : (
          <div className="flex h-64 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
            Select a price list to view its entries.
          </div>
        )}
      </div>

      <PriceListFormDialog open={formOpen} onOpenChange={setFormOpen} priceList={editingList} />
      <ConfirmDeleteDialog
        open={Boolean(deletingList)}
        onOpenChange={(open) => !open && setDeletingList(null)}
        title="Delete price list"
        description={
          <>
            This will permanently delete <strong>{deletingList?.name}</strong> and all of its
            entries. This action cannot be undone.
          </>
        }
        onConfirm={async () => {
          if (!deletingList) return;
          await deletePriceList.mutateAsync(deletingList.id);
          if (selectedId === deletingList.id) setSelectedId(null);
        }}
        isPending={deletePriceList.isPending}
      />
    </div>
  );
}

function EntriesTable({ priceList, canWrite }: { priceList: PriceListRead; canWrite: boolean }) {
  const { data, isLoading } = usePriceListEntries(priceList.id);
  const { data: productsPage } = useAllProducts();
  const deleteEntry = useDeletePriceListEntry();

  const [formOpen, setFormOpen] = React.useState(false);
  const [editingEntry, setEditingEntry] = React.useState<PriceListEntryRead | null>(null);
  const [deletingEntry, setDeletingEntry] = React.useState<PriceListEntryRead | null>(null);

  // Entries only carry `product_id` — resolve the label from the products list.
  const productName = (entry: PriceListEntryRead) =>
    productsPage?.items.find((product) => product.id === entry.product_id)?.name ??
    `Product #${entry.product_id}`;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-medium">{priceList.name}</p>
          <p className="text-xs text-muted-foreground">
            {data?.total ?? 0} entr{data?.total === 1 ? "y" : "ies"}
          </p>
        </div>
        {canWrite && (
          <Button
            size="sm"
            onClick={() => {
              setEditingEntry(null);
              setFormOpen(true);
            }}
          >
            <Plus />
            Add entry
          </Button>
        )}
      </div>

      <div className="rounded-lg border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Product</TableHead>
              <TableHead className="text-right">Override price</TableHead>
              <TableHead className="text-right">Extra discount</TableHead>
              {canWrite && <TableHead className="w-[50px]" />}
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 3 }).map((_, index) => (
                <TableRow key={index}>
                  <TableCell colSpan={canWrite ? 4 : 3}>
                    <Skeleton className="h-4 w-full" />
                  </TableCell>
                </TableRow>
              ))
            ) : data && data.items.length > 0 ? (
              data.items.map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell>{productName(entry)}</TableCell>
                  <TableCell className="text-right">
                    {entry.override_price_minor != null ? (
                      <Money minor={entry.override_price_minor} currency={priceList.currency} />
                    ) : (
                      <span className="text-muted-foreground">List price</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <Bps value={entry.extra_discount_bps} />
                  </TableCell>
                  {canWrite && (
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            onClick={() => {
                              setEditingEntry(entry);
                              setFormOpen(true);
                            }}
                          >
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={() => setDeletingEntry(entry)}
                          >
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  )}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={canWrite ? 4 : 3}
                  className="h-24 text-center text-muted-foreground"
                >
                  No entries yet — this list falls back to each product's list price.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <EntryFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        priceList={priceList}
        entry={editingEntry}
      />
      <ConfirmDeleteDialog
        open={Boolean(deletingEntry)}
        onOpenChange={(open) => !open && setDeletingEntry(null)}
        title="Delete entry"
        description="This will remove the price override for this product in this list."
        onConfirm={() =>
          deletingEntry &&
          deleteEntry.mutateAsync({ priceListId: priceList.id, entryId: deletingEntry.id })
        }
        isPending={deleteEntry.isPending}
      />
    </div>
  );
}
