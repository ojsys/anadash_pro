# dashboard/management/commands/fetch_ona_data.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from dashboard.utils.ona_client import ONAClient
from dashboard.utils.data_processor import process_dissemination_event
from dashboard.models import Partner, DataSyncLog

class Command(BaseCommand):
    help = 'Fetch data from ONA and store in local database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting ONA data fetch..."))
        
        ona_client = ONAClient()
        partner = Partner.objects.first()
        
        if not partner:
            self.stdout.write(self.style.ERROR("No partner found in database"))
            return

        sync_log = DataSyncLog.objects.create(
            partner=partner,
            sync_type='pull',
            start_time=timezone.now(),
            status='in_progress'
        )

        try:
            self.stdout.write("Fetching data from ONA...")
            events_data = ona_client.fetch_dissemination_events()
            
            total_records = len(events_data)
            self.stdout.write(self.style.SUCCESS(f"Found {total_records} records to process"))
            
            processed = 0
            failed = 0
            errors = []

            # Process records with progress indicator
            for i, event_data in enumerate(events_data, 1):
                success, error = process_dissemination_event(event_data, partner)
                if success:
                    processed += 1
                else:
                    failed += 1
                    errors.append(error)
                
                # Show progress every 100 records
                if i % 100 == 0:
                    self.stdout.write(f"Processed {i}/{total_records} records...")

            # Update sync log
            sync_log.status = 'success'
            sync_log.records_processed = processed
            sync_log.errors = "\n".join(errors) if errors else ""
            sync_log.end_time = timezone.now()
            sync_log.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSync completed:\n"
                    f"- Total records: {total_records}\n"
                    f"- Successfully processed: {processed}\n"
                    f"- Failed: {failed}"
                )
            )

        except Exception as e:
            sync_log.status = 'failed'
            sync_log.errors = str(e)
            sync_log.end_time = timezone.now()
            sync_log.save()
            
            self.stdout.write(
                self.style.ERROR(f"Error during sync: {str(e)}")
            )