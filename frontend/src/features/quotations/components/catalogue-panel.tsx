"use client";

import * as React from "react";
import { Plus, Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { useDebounce } from "@/lib/use-debounce";
import type { ProductRead } from "@/lib/api/types";
import { useCategories, useProducts } from "@/features/catalog/hooks";

const ALL_CATEGORIES = "all";
const PAGE_SIZE = 20;

interface CataloguePanelProps {
  onAdd: (product: ProductRead) => void;
  disabledProductIds?: number[];
}

/** Left column of the builder — search, category filter, add to quote.
 * `staleTime: 30_000` on the underlying query (Task 2 performance discipline):
 * the catalogue doesn't change while a rep is mid-edit. */
export function CataloguePanel({ onAdd }: CataloguePanelProps) {
  const [searchInput, setSearchInput] = React.useState("");
  const search = useDebounce(searchInput);
  const [categoryFilter, setCategoryFilter] = React.useState(ALL_CATEGORIES);

  const { data: categoriesPage } = useCategories();
  const { data, isLoading } = useProducts({
    page: 1,
    page_size: PAGE_SIZE,
    search: search || undefined,
    category_id: categoryFilter === ALL_CATEGORIES ? undefined : Number(categoryFilter),
    is_active: true,
  });

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="space-y-2">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search catalogue..."
            className="pl-9"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
          />
        </div>
        <Select value={categoryFilter} onValueChange={setCategoryFilter}>
          <SelectTrigger>
            <SelectValue placeholder="All categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_CATEGORIES}>All categories</SelectItem>
            {categoriesPage?.items.map((category) => (
              <SelectItem key={category.id} value={String(category.id)}>
                {category.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex-1 space-y-1.5 overflow-y-auto">
        {isLoading ? (
          Array.from({ length: 6 }).map((_, index) => <Skeleton key={index} className="h-16 w-full" />)
        ) : data && data.items.length > 0 ? (
          data.items.map((product) => (
            <button
              key={product.id}
              type="button"
              onClick={() => onAdd(product)}
              className="flex w-full items-center justify-between gap-2 rounded-lg border bg-card p-2.5 text-left shadow-sm transition-colors hover:bg-accent"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{product.name}</p>
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span>{product.category_name}</span>
                  {product.is_promoted && (
                    <Badge variant="info" className="px-1.5 py-0 text-[10px]">
                      Promoted
                    </Badge>
                  )}
                </div>
                <p className="text-xs font-medium tabular-nums">
                  <Money minor={product.list_price_minor} currency={product.currency} />
                </p>
              </div>
              <Plus className="h-4 w-4 shrink-0 text-muted-foreground" />
            </button>
          ))
        ) : (
          <p className="p-4 text-center text-sm text-muted-foreground">No products found.</p>
        )}
      </div>
    </div>
  );
}
