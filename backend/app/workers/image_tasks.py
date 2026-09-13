"""Background image processing: resizing/optimizing uploaded profile,
shop, and portfolio photos before/after storage upload."""
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.image_tasks.process_uploaded_image_task")
def process_uploaded_image_task(storage_key: str):
    # Resize to standard dimensions, strip EXIF/location metadata from
    # user-uploaded photos (privacy), and generate a thumbnail variant.
    raise NotImplementedError("Wire in an image processing library (e.g. Pillow) here.")
