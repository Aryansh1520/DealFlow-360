"use client";

import * as React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Plus, Trash2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { BpsInput } from "@/components/ui/bps-input";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { MoneyInput } from "@/components/ui/money-input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/features/auth/auth-context";
import type { ProductRead } from "@/lib/api/types";
import { useEnums } from "@/features/meta/hooks";
import {
  useCategories,
  useCreateProduct,
  useCreateVariant,
  useDeleteVariant,
  useUpdateProduct,
  useUpdateVariant,
} from "@/features/catalog/hooks";
import { useAllSubscriptionPlans } from "@/features/subscriptions/hooks";

const productSchema = z.object({
  sku: z.string().min(1, "SKU is required"),
  name: z.string().min(1, "Name is required"),
  category_id: z.string().min(1, "Category is required"),
  description: z.string(),
  unit: z.string().min(1, "Unit is required"),
  list_price_minor: z.coerce.number().int().min(0),
  cost_price_minor: z.coerce.number().int().min(0),
  tax_bps: z.coerce.number().int().min(0),
  is_promoted: z.boolean(),
  line_type: z.enum(["one_time", "subscription"]),
  subscription_plan_id: z.string(),
  currency: z.string().length(3, "3-letter currency code"),
  is_active: z.boolean(),
});

type ProductValues = z.infer<typeof productSchema>;

interface VariantRow {
  key: string;
  id?: number;
  attribute: string;
  value: string;
  extra_price_minor: number;
}

function toRows(product?: ProductRead | null): VariantRow[] {
  return (product?.variants ?? []).map((v) => ({
    key: String(v.id),
    id: v.id,
    attribute: v.attribute,
    value: v.value,
    extra_price_minor: v.extra_price_minor,
  }));
}

interface ProductFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  product?: ProductRead | null;
}

export function ProductFormDialog({ open, onOpenChange, product }: ProductFormDialogProps) {
  const isEdit = Boolean(product);
  const { hasPermission } = useAuth();
  const canSeeCost = hasPermission("catalog:write");

  const { data: categoriesPage } = useCategories();
  const { data: plansPage } = useAllSubscriptionPlans();
  const { data: enums } = useEnums();

  const createProduct = useCreateProduct();
  const updateProduct = useUpdateProduct();
  const createVariant = useCreateVariant();
  const updateVariant = useUpdateVariant();
  const deleteVariant = useDeleteVariant();

  const [rows, setRows] = React.useState<VariantRow[]>([]);
  const [removedIds, setRemovedIds] = React.useState<number[]>([]);
  const [savingVariants, setSavingVariants] = React.useState(false);

  const form = useForm<ProductValues>({
    resolver: zodResolver(productSchema),
    defaultValues: {
      sku: "",
      name: "",
      category_id: "",
      description: "",
      unit: "unit",
      list_price_minor: 0,
      cost_price_minor: 0,
      tax_bps: 0,
      is_promoted: false,
      line_type: "one_time",
      subscription_plan_id: "",
      currency: "INR",
      is_active: true,
    },
  });

  const lineType = form.watch("line_type");

  React.useEffect(() => {
    if (open) {
      form.reset({
        sku: product?.sku ?? "",
        name: product?.name ?? "",
        category_id: product ? String(product.category_id) : "",
        description: product?.description ?? "",
        unit: product?.unit ?? "unit",
        list_price_minor: product?.list_price_minor ?? 0,
        cost_price_minor: product?.cost_price_minor ?? 0,
        tax_bps: product?.tax_bps ?? 0,
        is_promoted: product?.is_promoted ?? false,
        line_type: product?.line_type ?? "one_time",
        subscription_plan_id: product?.subscription_plan_id
          ? String(product.subscription_plan_id)
          : "",
        currency: product?.currency ?? "INR",
        is_active: true,
      });
      setRows(toRows(product));
      setRemovedIds([]);
    }
  }, [open, product, form]);

  const addRow = () => {
    setRows((current) => [
      ...current,
      { key: crypto.randomUUID(), attribute: "", value: "", extra_price_minor: 0 },
    ]);
  };

  const updateRow = (key: string, patch: Partial<VariantRow>) => {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  };

  const removeRow = (key: string) => {
    setRows((current) => {
      const row = current.find((r) => r.key === key);
      if (row?.id) setRemovedIds((ids) => [...ids, row.id!]);
      return current.filter((r) => r.key !== key);
    });
  };

  const persistVariants = async (productId: number) => {
    setSavingVariants(true);
    try {
      for (const id of removedIds) {
        await deleteVariant.mutateAsync({ productId, variantId: id });
      }
      for (const row of rows) {
        if (!row.attribute.trim() || !row.value.trim()) continue;
        if (row.id) {
          const original = toRows(product).find((r) => r.id === row.id);
          if (
            original &&
            original.attribute === row.attribute &&
            original.value === row.value &&
            original.extra_price_minor === row.extra_price_minor
          ) {
            continue;
          }
          await updateVariant.mutateAsync({
            productId,
            variantId: row.id,
            payload: {
              attribute: row.attribute,
              value: row.value,
              extra_price_minor: row.extra_price_minor,
            },
          });
        } else {
          await createVariant.mutateAsync({
            productId,
            payload: {
              attribute: row.attribute,
              value: row.value,
              extra_price_minor: row.extra_price_minor,
            },
          });
        }
      }
    } finally {
      setSavingVariants(false);
    }
  };

  const onSubmit = async (values: ProductValues) => {
    const payload = {
      sku: values.sku,
      name: values.name,
      category_id: Number(values.category_id),
      description: values.description || null,
      unit: values.unit,
      list_price_minor: values.list_price_minor,
      cost_price_minor: values.cost_price_minor,
      tax_bps: values.tax_bps,
      is_promoted: values.is_promoted,
      line_type: values.line_type,
      subscription_plan_id:
        values.line_type === "subscription" && values.subscription_plan_id
          ? Number(values.subscription_plan_id)
          : null,
      currency: values.currency.toUpperCase(),
      is_active: values.is_active,
    };

    if (isEdit && product) {
      await updateProduct.mutateAsync({ id: product.id, payload });
      await persistVariants(product.id);
    } else {
      const created = await createProduct.mutateAsync(payload);
      await persistVariants(created.id);
    }
    onOpenChange(false);
  };

  const isPending = createProduct.isPending || updateProduct.isPending || savingVariants;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit product" : "New product"}</DialogTitle>
          <DialogDescription>
            {isEdit ? "Update the product's catalogue details." : "Add a product to the catalogue."}
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="sku"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>SKU</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="category_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Category</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select a category" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {categoriesPage?.items.map((category) => (
                          <SelectItem key={category.id} value={String(category.id)}>
                            {category.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="unit"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Unit</FormLabel>
                    <FormControl>
                      <Input placeholder="unit, hour, licence…" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description (optional)</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-3 gap-4">
              <FormField
                control={form.control}
                name="list_price_minor"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>List price</FormLabel>
                    <FormControl>
                      <MoneyInput
                        value={field.value}
                        onChange={field.onChange}
                        currency={form.watch("currency")}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              {canSeeCost && (
                <FormField
                  control={form.control}
                  name="cost_price_minor"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Cost price</FormLabel>
                      <FormControl>
                        <MoneyInput
                          value={field.value}
                          onChange={field.onChange}
                          currency={form.watch("currency")}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}
              <FormField
                control={form.control}
                name="tax_bps"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Tax</FormLabel>
                    <FormControl>
                      <BpsInput value={field.value} onChange={field.onChange} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="line_type"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Line type</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {(enums?.line_type ?? ["one_time", "subscription"]).map((type) => (
                          <SelectItem key={type} value={type}>
                            {enums?.labels.line_type?.[type] ?? type}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              {lineType === "subscription" && (
                <FormField
                  control={form.control}
                  name="subscription_plan_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Subscription plan</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select a plan" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {plansPage?.items.map((plan) => (
                            <SelectItem key={plan.id} value={String(plan.id)}>
                              {plan.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}
            </div>

            <div className="flex items-center gap-6">
              <FormField
                control={form.control}
                name="is_promoted"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center gap-2 space-y-0">
                    <FormControl>
                      <Checkbox checked={field.value} onCheckedChange={field.onChange} />
                    </FormControl>
                    <FormLabel className="font-normal">Promoted</FormLabel>
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="is_active"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center gap-2 space-y-0">
                    <FormControl>
                      <Checkbox checked={field.value} onCheckedChange={field.onChange} />
                    </FormControl>
                    <FormLabel className="font-normal">Active</FormLabel>
                  </FormItem>
                )}
              />
            </div>

            <Separator />

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">Variants</p>
                <Button type="button" variant="outline" size="sm" onClick={addRow}>
                  <Plus />
                  Add variant
                </Button>
              </div>
              {rows.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No variants — this product sells as a single SKU.
                </p>
              ) : (
                <div className="space-y-2">
                  {rows.map((row) => (
                    <div key={row.key} className="flex items-center gap-2">
                      <Input
                        placeholder="Attribute (Size)"
                        value={row.attribute}
                        onChange={(event) => updateRow(row.key, { attribute: event.target.value })}
                      />
                      <Input
                        placeholder="Value (Large)"
                        value={row.value}
                        onChange={(event) => updateRow(row.key, { value: event.target.value })}
                      />
                      <MoneyInput
                        value={row.extra_price_minor}
                        onChange={(minor) => updateRow(row.key, { extra_price_minor: minor })}
                        currency={form.watch("currency")}
                        className="w-40"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => removeRow(row.key)}
                      >
                        <Trash2 className="text-destructive" />
                        <span className="sr-only">Remove variant</span>
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending && <Loader2 className="animate-spin" />}
                {isEdit ? "Save changes" : "Create product"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
