"use client";

import * as React from "react";
import { ChevronLeft, ChevronRight, MoreHorizontal, Plus, Search } from "lucide-react";

import { getErrorMessage } from "@/lib/api-client";
import { useDebounce } from "@/lib/use-debounce";
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
import { Input } from "@/components/ui/input";
import { Money } from "@/components/ui/money";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import type { ProductRead } from "@/lib/api/types";
import { ProductFormDialog } from "@/features/catalog/components/product-form-dialog";
import { useCategories, useDeleteProduct, useProducts } from "@/features/catalog/hooks";
import { useAllSubscriptionPlans } from "@/features/subscriptions/hooks";

const PAGE_SIZE = 10;
const ALL = "all";

export function ProductsTable() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("catalog:write");
  const canSeeCost = canWrite;

  const [page, setPage] = React.useState(1);
  const [searchInput, setSearchInput] = React.useState("");
  const search = useDebounce(searchInput);
  const [categoryFilter, setCategoryFilter] = React.useState<string>(ALL);

  const [formOpen, setFormOpen] = React.useState(false);
  const [editingProduct, setEditingProduct] = React.useState<ProductRead | null>(null);
  const [deletingProduct, setDeletingProduct] = React.useState<ProductRead | null>(null);

  const { data: categoriesPage } = useCategories();
  const { data: plansPage } = useAllSubscriptionPlans();
  const planInterval = (planId: number | null) =>
    plansPage?.items.find((plan) => plan.id === planId)?.interval ?? null;
  const { data, isLoading, isError, error } = useProducts({
    page,
    page_size: PAGE_SIZE,
    search: search || undefined,
    category_id: categoryFilter === ALL ? undefined : Number(categoryFilter),
    sort_by: "created_at",
    sort_order: "desc",
  });
  const deleteProduct = useDeleteProduct();

  React.useEffect(() => {
    setPage(1);
  }, [search, categoryFilter]);

  const openCreate = () => {
    setEditingProduct(null);
    setFormOpen(true);
  };

  const openEdit = (product: ProductRead) => {
    setEditingProduct(product);
    setFormOpen(true);
  };

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Failed to load products</AlertTitle>
        <AlertDescription>{getErrorMessage(error)}</AlertDescription>
      </Alert>
    );
  }

  const columnCount = 5 + (canSeeCost ? 1 : 0) + (canWrite ? 1 : 0);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative w-full max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search products..."
              className="pl-9"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
            />
          </div>
          <Select value={categoryFilter} onValueChange={setCategoryFilter}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="All categories" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All categories</SelectItem>
              {categoriesPage?.items.map((category) => (
                <SelectItem key={category.id} value={String(category.id)}>
                  {category.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {canWrite && (
          <Button onClick={openCreate}>
            <Plus />
            Add product
          </Button>
        )}
      </div>

      <div className="rounded-lg border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Product</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">List price</TableHead>
              {canSeeCost && <TableHead className="text-right">Cost price</TableHead>}
              {canWrite && <TableHead className="w-[50px]" />}
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 6 }).map((_, index) => (
                <TableRow key={index}>
                  {Array.from({ length: columnCount }).map((__, cell) => (
                    <TableCell key={cell}>
                      <Skeleton className="h-4 w-20" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : data && data.items.length > 0 ? (
              data.items.map((product) => (
                <TableRow key={product.id}>
                  <TableCell>
                    <p className="font-medium">{product.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {product.sku}
                      {product.variants.length > 0 &&
                        ` · ${product.variants.length} variant${product.variants.length > 1 ? "s" : ""}`}
                    </p>
                  </TableCell>
                  <TableCell>{product.category_name}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Badge variant="secondary" className="capitalize">
                        {product.line_type.replace("_", " ")}
                      </Badge>
                      {product.line_type === "subscription" && (
                        <Badge variant="outline" className="capitalize">
                          {planInterval(product.subscription_plan_id) ?? "No plan"}
                        </Badge>
                      )}
                      {product.is_promoted && <Badge variant="info">Promoted</Badge>}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={product.is_active ? "positive" : "outline"}>
                      {product.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Money minor={product.list_price_minor} currency={product.currency} />
                  </TableCell>
                  {canSeeCost && (
                    <TableCell className="text-right text-muted-foreground">
                      <Money minor={product.cost_price_minor} currency={product.currency} />
                    </TableCell>
                  )}
                  {canWrite && (
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal />
                            <span className="sr-only">Open actions</span>
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => openEdit(product)}>
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={() => setDeletingProduct(product)}
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
                <TableCell colSpan={columnCount} className="h-24 text-center text-muted-foreground">
                  No products found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {data && data.pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {data.page} of {data.pages} · {data.total} products
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((current) => current - 1)}
            >
              <ChevronLeft />
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= data.pages}
              onClick={() => setPage((current) => current + 1)}
            >
              Next
              <ChevronRight />
            </Button>
          </div>
        </div>
      )}

      <ProductFormDialog open={formOpen} onOpenChange={setFormOpen} product={editingProduct} />
      <ConfirmDeleteDialog
        open={Boolean(deletingProduct)}
        onOpenChange={(open) => !open && setDeletingProduct(null)}
        title="Delete product"
        description={
          <>
            This will permanently delete <strong>{deletingProduct?.name}</strong>. This action
            cannot be undone.
          </>
        }
        onConfirm={() => deletingProduct && deleteProduct.mutateAsync(deletingProduct.id)}
        isPending={deleteProduct.isPending}
      />
    </div>
  );
}
