"""Background AI tasks: anything that shouldn't block a chat response,
e.g. summarizing long conversations or precomputing search-filter
extraction for trending queries."""
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.ai_tasks.summarize_ai_conversation_task")
def summarize_ai_conversation_task(conversation_id: str):
    raise NotImplementedError("Wire in ai_service conversation summarization here.")
