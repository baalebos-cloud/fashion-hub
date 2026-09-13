"""Background invoice/receipt generation, kept off the payment-confirmation
request path so webhook/callback handlers respond quickly to the provider."""
from app.core.database import session_scope
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.invoice_tasks.generate_invoice_for_order_task", bind=True, max_retries=3)
def generate_invoice_for_order_task(self, order_id: str):
    from app.services.invoice_service import InvoiceService

    with session_scope() as db:
        InvoiceService(db).generate_for_order(order_id)


@celery_app.task(name="app.workers.invoice_tasks.render_invoice_pdf_task")
def render_invoice_pdf_task(invoice_id: str):
    from app.services.invoice_service import InvoiceService

    with session_scope() as db:
        InvoiceService(db).render_pdf(invoice_id)
