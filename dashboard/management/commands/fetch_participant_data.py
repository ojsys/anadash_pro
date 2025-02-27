from django.core.management.base import BaseCommand
from django.utils import timezone
from dashboard.utils.ona_client import ONAClient
from dashboard.utils.data_processor import (
    process_participant,
    process_farmer,
    process_extension_agent
)
from dashboard.models import Partner, DataSyncLog

class Command(BaseCommand):
    help = 'Fetch participant data (farmers and extension agents) from ONA'

    def _process_data(self, data_list, processor_func, data_type):
        """Helper method to process a list of data items"""
        processed = 0
        failed = 0
        errors = []

        for i, item in enumerate(data_list, 1):
            success, error = processor_func(item)
            if success:
                processed += 1
            else:
                failed += 1
                errors.append(f"{data_type} error: {error}")

            if i % 50 == 0:  # Progress update every 50 records
                self.stdout.write(f"Processed {i} {data_type}s...")

        return processed, failed, errors

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting participant data fetch..."))
        
        ona_client = ONAClient()
        partner = Partner.objects.first()
        
        if not partner:
            self.stdout.write(self.style.ERROR("No partner found in database"))
            return

        sync_log = DataSyncLog.objects.create(
            partner=partner,
            sync_type='pull_participants',
            start_time=timezone.now(),
            status='in_progress'
        )

        try:
            total_processed = 0
            total_failed = 0
            all_errors = []

            # Fetch and process farmers
            self.stdout.write("\nFetching farmers data...")
            farmers_data = ona_client.fetch_farmers()
            self.stdout.write(f"Found {len(farmers_data)} farmer records")
            
            processed, failed, errors = self._process_data(farmers_data, process_farmer, 'Farmer')
            total_processed += processed
            total_failed += failed
            all_errors.extend(errors)
            self.stdout.write(self.style.SUCCESS(
                f"Processed {processed} farmers, {failed} failed"
            ))

            # Fetch and process extension agents
            self.stdout.write("\nFetching extension agents data...")
            agents_data = ona_client.fetch_extension_agents()
            self.stdout.write(f"Found {len(agents_data)} extension agent records")
            
            processed, failed, errors = self._process_data(
                agents_data, process_extension_agent, 'Extension Agent'
            )
            total_processed += processed
            total_failed += failed
            all_errors.extend(errors)
            self.stdout.write(self.style.SUCCESS(
                f"Processed {processed} extension agents, {failed} failed"
            ))

            # Update sync log
            sync_log.status = 'success' if not all_errors else 'partial'
            sync_log.records_processed = total_processed
            sync_log.errors = "\n".join(all_errors) if all_errors else ""
            sync_log.end_time = timezone.now()
            sync_log.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nParticipant sync completed:\n"
                    f"- Total processed: {total_processed}\n"
                    f"- Total failed: {total_failed}\n"
                    f"- Errors: {len(all_errors)}"
                )
            )

        except Exception as e:
            sync_log.status = 'failed'
            sync_log.errors = str(e)
            sync_log.end_time = timezone.now()
            sync_log.save()
            
            self.stdout.write(
                self.style.ERROR(f"Error during participant sync: {str(e)}")
            )