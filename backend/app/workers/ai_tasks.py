"""Background AI tasks: anything that shouldn't block a chat response,
e.g. summarizing long conversations or precomputing search-filter
extraction for trending queries."""
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.ai_tasks.summarize_ai_conversation_task")
def summarize_ai_conversation_task(conversation_id: str):
    raise NotImplementedError("Wire in ai_service conversation summarization here.")


"""Asynchronous tailoring estimates; no image bytes are placed in Redis.

Only an unapproved audit note is persisted. Inventory, payments and
order status remain unchanged until an authorized professional approves.
"""
from uuid import UUID
from app.core.config import settings
from app.core.database import session_scope
from app.models.order import Order
from app.models.order_timeline import OrderTimelineEntry
from app.services.vertex_service import VertexAIService, VertexUnavailable
from app.workers.celery_app import celery_app


def _is_rate_limited(exc: Exception) -> bool:
    return getattr(exc, "status_code", None) == 429 or getattr(exc, "code", None) == 429


@celery_app.task(name="app.workers.ai_tasks.generate_tailoring_draft", bind=True, max_retries=5, acks_late=True)
def generate_tailoring_draft(self, order_id: str, actor_id: str, prompt: str):
    if not settings.VERTEX_AI_ENABLED or not settings.GCP_PROJECT_ID:
        return {"status": "disabled"}
    if not prompt.strip() or len(prompt) > 6000:
        raise ValueError("Description must contain 1-6000 characters.")
    order_uuid, actor_uuid = UUID(order_id), UUID(actor_id)
    with session_scope() as db:
        order = db.get(Order, order_uuid)
        if not order or order.order_type != "customer_order" or order.seller_user_id != actor_uuid:
            return {"status": "forbidden"}
    try:
        result = VertexAIService().generate_tailoring_spec(prompt)
    except VertexUnavailable:
        return {"status": "disabled"}
    except Exception as exc:
        if _is_rate_limited(exc) and self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=min(30 * (2 ** self.request.retries), 900))
        raise

    with session_scope() as db:
        order = db.query(Order).filter(Order.id == order_uuid).with_for_update().first()
        if not order or order.seller_user_id != actor_uuid:
            return {"status": "forbidden"}
        marker = f"[AI-DRAFT task={self.request.id}]"
        existing = db.query(OrderTimelineEntry).filter(
            OrderTimelineEntry.order_id == order.id,
            OrderTimelineEntry.note.like(f"{marker}%"),
        ).first()
        if not existing:
            db.add(OrderTimelineEntry(
                order_id=order.id, actor_user_id=actor_uuid,
                from_status=order.status, to_status=order.status,
                note=(f"{marker} Estimated {result.estimated_fabric_yards:.2f} yards; "
                      "tailor confirmation required; no vendor order or payment initiated."),
            ))
    return {"status": "review_required", "estimated_fabric_yards": result.estimated_fabric_yards}
