# dashboard/management/commands/fetch_ona_data.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from dashboard.utils.ona_client import ONAClient
from dashboard.utils.data_processor import process_dissemination_event
from dashboard.models import DataSyncLog

class Command(BaseCommand):
    help = 'Fetch data from ONA and store in local database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting ONA data fetch..."))
        
        # Initialize ONA client
        ona_client = ONAClient()

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
                success, error = process_dissemination_event(event_data)
                if success:
                    processed += 1
                else:
                    failed += 1
                    errors.append(f"Event ID {event_data.get('_id')}: {error}")
                
                # Show progress every 100 records
                if i % 100 == 0:
                    self.stdout.write(f"Processed {i}/{total_records} records...")

            # Final summary
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSync completed:\n"
                    f"- Total records: {total_records}\n"
                    f"- Successfully processed: {processed}\n"
                    f"- Failed: {failed}"
                )
            )
            
            if errors:
                self.stdout.write("\nErrors encountered:")
                for error in errors[:10]:  # Show first 10 errors
                    self.stdout.write(self.style.WARNING(f"- {error}"))
                if len(errors) > 10:
                    self.stdout.write(f"... and {len(errors) - 10} more errors")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error during sync: {str(e)}")
            )