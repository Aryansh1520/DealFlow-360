"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { getErrorMessage } from "@/lib/api-client";
import type { PaymentRequest, SupersedeRequest } from "@/lib/api/types";
import { QUOTATIONS_KEY } from "@/features/quotations/hooks";
import { billingApi } from "@/features/billing/api";

const BILLING_KEY = "billing";

export function useBillingSchedule(quotationId: number) {
  return useQuery({
    queryKey: [BILLING_KEY, quotationId, "schedule"],
    queryFn: () => billingApi.schedule(quotationId),
    enabled: Number.isFinite(quotationId) && quotationId > 0,
  });
}

export function useInvoices(quotationId: number) {
  return useQuery({
    queryKey: [BILLING_KEY, quotationId, "invoices"],
    queryFn: () => billingApi.listInvoices({ quotation_id: quotationId, page_size: 100 }),
    enabled: Number.isFinite(quotationId) && quotationId > 0,
  });
}

export function useInvoiceLineage(invoiceId: number | null) {
  return useQuery({
    queryKey: [BILLING_KEY, "lineage", invoiceId],
    queryFn: () => billingApi.lineage(invoiceId!),
    enabled: invoiceId != null,
  });
}

function useInvalidateBilling(quotationId: number) {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: [BILLING_KEY, quotationId] });
    qc.invalidateQueries({ queryKey: [QUOTATIONS_KEY, quotationId] });
    qc.invalidateQueries({ queryKey: [QUOTATIONS_KEY, quotationId, "events"] });
  };
}

export function useGenerateInvoice(quotationId: number) {
  const invalidate = useInvalidateBilling(quotationId);
  return useMutation({
    mutationFn: (idempotencyKey: string) => billingApi.generateInvoice(quotationId, idempotencyKey),
    onSuccess: (invoice) => {
      invalidate();
      toast.success(`Invoice ${invoice.number} issued`);
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useRecordPayment(quotationId: number, invoiceId: number) {
  const invalidate = useInvalidateBilling(quotationId);
  return useMutation({
    mutationFn: ({
      payload,
      idempotencyKey,
    }: {
      payload: PaymentRequest;
      idempotencyKey: string;
    }) => billingApi.recordPayment(invoiceId, payload, idempotencyKey),
    onSuccess: (invoice) => {
      invalidate();
      toast.success(
        invoice.status === "paid" ? "Paid in full — quotation moved to Paid" : "Payment recorded"
      );
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useSupersedeInvoice(quotationId: number, invoiceId: number) {
  const invalidate = useInvalidateBilling(quotationId);
  return useMutation({
    mutationFn: ({
      payload,
      idempotencyKey,
    }: {
      payload: SupersedeRequest;
      idempotencyKey: string;
    }) => billingApi.supersede(invoiceId, payload, idempotencyKey),
    onSuccess: (res) => {
      invalidate();
      toast.success(`${res.credit_note.number} issued · ${res.new_invoice.number} replaces the original`);
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useDownloadInvoicePdf() {
  return useMutation({
    mutationFn: ({ id, number }: { id: number; number: string }) =>
      billingApi.downloadPdf(id, number),
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export { BILLING_KEY };
