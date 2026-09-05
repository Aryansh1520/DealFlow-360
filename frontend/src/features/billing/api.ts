import { apiClient } from "@/lib/api-client";
import type {
  BillingScheduleEntry,
  InvoiceRead,
  PaymentRequest,
  SupersedeRequest,
  SupersedeResponse,
} from "@/lib/api/types";
import type { Page } from "@/lib/types";

export const billingApi = {
  schedule: async (quotationId: number): Promise<BillingScheduleEntry[]> => {
    const { data } = await apiClient.get<BillingScheduleEntry[]>(
      `/quotations/${quotationId}/billing-schedule`
    );
    return data;
  },

  generateInvoice: async (quotationId: number, idempotencyKey: string): Promise<InvoiceRead> => {
    const { data } = await apiClient.post<InvoiceRead>(
      `/quotations/${quotationId}/invoices/generate`,
      {},
      { headers: { "Idempotency-Key": idempotencyKey } }
    );
    return data;
  },

  listInvoices: async (params: {
    quotation_id?: number;
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<Page<InvoiceRead>> => {
    const { data } = await apiClient.get<Page<InvoiceRead>>("/invoices", { params });
    return data;
  },

  getInvoice: async (id: number): Promise<InvoiceRead> => {
    const { data } = await apiClient.get<InvoiceRead>(`/invoices/${id}`);
    return data;
  },

  lineage: async (id: number): Promise<InvoiceRead[]> => {
    const { data } = await apiClient.get<InvoiceRead[]>(`/invoices/${id}/lineage`);
    return data;
  },

  /** Streams the PDF as a blob so the `Authorization` header is sent (a plain
   * `<a href>` would 401). Caller creates an object URL and opens it. */
  downloadPdf: async (id: number, number: string): Promise<void> => {
    const response = await apiClient.get(`/invoices/${id}/pdf`, { responseType: "blob" });
    const blob = new Blob([response.data as BlobPart], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${number}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },

  recordPayment: async (
    id: number,
    payload: PaymentRequest,
    idempotencyKey: string
  ): Promise<InvoiceRead> => {
    const { data } = await apiClient.post<InvoiceRead>(`/invoices/${id}/payments`, payload, {
      headers: { "Idempotency-Key": idempotencyKey },
    });
    return data;
  },

  supersede: async (
    id: number,
    payload: SupersedeRequest,
    idempotencyKey: string
  ): Promise<SupersedeResponse> => {
    const { data } = await apiClient.post<SupersedeResponse>(`/invoices/${id}/supersede`, payload, {
      headers: { "Idempotency-Key": idempotencyKey },
    });
    return data;
  },
};
