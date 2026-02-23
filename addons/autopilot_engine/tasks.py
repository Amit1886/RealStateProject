import logging

from celery import shared_task

from addons.autopilot_engine.services.executor import RetryableEventError, execute_event

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5)
def process_autopilot_event(self, event_id: int):
    try:
        execute_event(event_id)
    except RetryableEventError as exc:
        countdown = min(60 * (2 ** self.request.retries), 900)
        raise self.retry(exc=exc, countdown=countdown)


@shared_task
def run_backup_job(backup_job_id: int):
    from addons.autopilot_engine.models import BackupJob

    job = BackupJob.objects.filter(id=backup_job_id).first()
    if not job:
        return
    job.status = BackupJob.Status.RUNNING
    job.save(update_fields=["status", "updated_at"])
    job.status = BackupJob.Status.DONE
    job.save(update_fields=["status", "updated_at"])
