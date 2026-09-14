# Invoice Flow

Invoices are generated server-side, automatically, after a payment is
confirmed (see `backend/docs/invoices.md`) — there is no "generate
invoice" action anywhere in this frontend. `pages/customer/Invoices.tsx`
and its professional/vendor equivalents are read-only lists;
`InvoiceDetails.tsx` fetches by order ID and `InvoiceDownload.tsx` simply
opens the PDF URL the backend already produced.
