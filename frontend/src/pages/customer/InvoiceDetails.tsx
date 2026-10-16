import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { invoicesApi } from "@/api/invoices.api";
import { InvoiceDetails as InvoiceDetailsComponent } from "@/components/invoices/InvoiceDetails";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { Invoice } from "@/types/invoice";

export default function InvoiceDetails() {
  const { invoiceId } = useParams<{ invoiceId: string }>();
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setInvoice(null);
    setError(null);
    if (invoiceId) invoicesApi.getById(invoiceId)
      .then((data) => { if (active) setInvoice(data); })
      .catch((err) => { if (active) setError(getDisplayErrorMessage(err)); });
    return () => { active = false; };
  }, [invoiceId, attempt]);
  if (error) return <div className="flex flex-col gap-3"><p role="alert" className="text-thread">{error}</p><Button onClick={() => setAttempt((value) => value + 1)}>Try again</Button></div>;
  if (!invoice || invoice.id !== invoiceId) return <LoadingScreen label="Loading invoice…" />;
  return <InvoiceDetailsComponent invoice={invoice} />;
}
