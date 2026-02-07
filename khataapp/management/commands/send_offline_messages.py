from django.core.management.base import BaseCommand
from khataapp.models import OfflineMessage
from khataapp.utils.whatsapp_utils import send_whatsapp_message


class Command(BaseCommand):
    help = "Send pending OfflineMessage entries (WhatsApp only)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50, help="Max messages to process")

    def handle(self, *args, **options):
        limit = options["limit"]
        pending = OfflineMessage.objects.filter(channel="whatsapp", status="pending").order_by("created_at")[:limit]

        sent = 0
        failed = 0
        skipped = 0

        for msg in pending:
            party = msg.party
            if not party:
                mobile = msg.recipient_mobile
            else:
                mobile = party.whatsapp_number or party.mobile

            if not mobile:
                msg.status = "failed"
                msg.save(update_fields=["status"])
                failed += 1
                continue

            try:
                send_whatsapp_message(mobile.lstrip("+"), msg.message)
                msg.status = "sent"
                msg.save(update_fields=["status"])
                sent += 1
            except Exception:
                msg.status = "failed"
                msg.save(update_fields=["status"])
                failed += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Sent={sent}, Failed={failed}, Skipped={skipped}"
        ))
