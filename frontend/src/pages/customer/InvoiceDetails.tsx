import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { invoicesApi } from "@/api/invoices.api";
import { InvoiceDetails as InvoiceDetailsComponent } from "@/components/invoices/InvoiceDetails";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import type { Invoice } from "@/types/invoice";

export default function InvoiceDetails() {
  const { invoiceId } = useParams<{ invoiceId: string }>();
  const [invoice, setInvoice] = useState<Invoice | null>(null);

  useEffect(() => {
    if (invoiceId) invoicesApi.getById(invoiceId).then(setInvoice);
  }, [invoiceId]);

  if (!invoice) return <LoadingScreen label="Loading invoice…" />;

  return <InvoiceDetailsComponent invoice={invoice} />;
}
