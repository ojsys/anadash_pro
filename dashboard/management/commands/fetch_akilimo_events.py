from django.core.management.base import BaseCommand
from dashboard.utils.akilimo_fetcher import AkilimoEventFetcher
from dashboard.utils.event_processor import EventProcessor
from django.utils import timezone
from dashboard.models import DataSyncLog
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetch AKILIMO events from ODK and store in database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting AKILIMO events fetch..."))
        
        # Create sync log
        sync_log = DataSyncLog.objects.create(
            partner_id=1,  # Default partner
            sync_type='pull',
            start_time=timezone.now(),
            status='in_progress'
        )

        try:
            # Initialize fetcher and processor
            fetcher = AkilimoEventFetcher()
            processor = EventProcessor()
            
            # Fetch events
            events = fetcher.fetch_events()
            
            if not events:
                self.stdout.write(self.style.WARNING("No events found or error occurred"))
                sync_log.status = 'failed'
                sync_log.end_time = timezone.now()
                sync_log.save()
                return

            # Process events
            processed = 0
            failed = 0
            errors = []
            
            for event in events:
                success, message = processor.process_event(event)
                if success:
                    processed += 1
                else:
                    failed += 1
                    errors.append(message)
                    self.stdout.write(self.style.WARNING(f"Failed to process event: {message}"))

            # Update sync log
            sync_log.status = 'success' if not errors else 'partial'
            sync_log.records_processed = processed
            sync_log.errors = "\n".join(errors) if errors else ""
            sync_log.end_time = timezone.now()
            sync_log.save()

            self.stdout.write(self.style.SUCCESS(
                f"\nSync completed:\n"
                f"- Total processed: {processed}\n"
                f"- Failed: {failed}\n"
                f"- Errors: {len(errors)}"
            ))

        except Exception as e:
            sync_log.status = 'failed'
            sync_log.errors = str(e)
            sync_log.end_time = timezone.now()
            sync_log.save()
            
            self.stdout.write(
                self.style.ERROR(f"Error during sync: {str(e)}")
            )
