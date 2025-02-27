from django.core.management.base import BaseCommand
from django.utils import timezone
from dashboard.utils.ona_client import ONAClient
from dashboard.utils.data_processor import (
    process_dissemination_event,
    process_partner,
    process_participant,
    process_extension_agent,
    process_farmer,
    process_scaling_checklist
)
from dashboard.models import Partner, DataSyncLog

class Command(BaseCommand):
    help = 'Fetch all data types from ONA and store in local database'

    def _process_data(self, data_list, processor_func, data_type):
        """Helper method to process a list of data items"""
        processed = 0
        failed = 0
        errors = []

        for item in data_list:
            success, error = processor_func(item)
            if success:
                processed += 1
            else:
                failed += 1
                errors.append(f"{data_type} error: {error}")

        return processed, failed, errors

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting ONA data fetch..."))
        
        ona_client = ONAClient()
        
        # Create a default partner if none exists
        partner, created = Partner.objects.get_or_create(
            name="Default Partner",
            defaults={'country': 'NG', 'is_active': True}
        )

        sync_log = DataSyncLog.objects.create(
            partner=partner,
            sync_type='pull',
            start_time=timezone.now(),
            status='in_progress'
        )

        try:
            total_processed = 0
            total_failed = 0
            all_errors = []

            # Process each data type and show progress
            data_types = [
                ('events', ona_client.fetch_dissemination_events, process_dissemination_event),
                ('extension_agents', ona_client.fetch_extension_agents, process_extension_agent),
                ('participants', ona_client.fetch_participants, process_participant),  # Changed this line
                ('checklists', ona_client.fetch_checklists, process_scaling_checklist)
            ]

            for data_type, fetch_func, process_func in data_types:
                self.stdout.write(f"\nFetching {data_type}...")
                try:
                    data = fetch_func()
                    processed, failed, errors = self._process_data(data, process_func, data_type)
                    total_processed += processed
                    total_failed += failed
                    all_errors.extend(errors)
                    self.stdout.write(f"Processed {processed} {data_type}, {failed} failed")

                    # Process farmers from participant data
                    if data_type == 'participants':
                        self.stdout.write("\nProcessing farmers from participant data...")
                        farmer_processed = 0
                        farmer_failed = 0
                        for item in data:
                            if item.get('participant_type') == 'farmer':  # Adjust this condition based on your data structure
                                success, error = process_farmer(item)
                                if success:
                                    farmer_processed += 1
                                else:
                                    farmer_failed += 1
                                    all_errors.append(f"Farmer error: {error}")
                        
                        total_processed += farmer_processed
                        total_failed += farmer_failed
                        self.stdout.write(f"Processed {farmer_processed} farmers, {farmer_failed} failed")

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing {data_type}: {str(e)}"))
                    all_errors.append(f"{data_type} fetch error: {str(e)}")

       

# # dashboard/management/commands/fetch_ona_data.py
# from django.core.management.base import BaseCommand
# from django.utils import timezone
# from dashboard.utils.ona_client import ONAClient
# from dashboard.utils.data_processor import process_dissemination_event
# from dashboard.models import Partner, DataSyncLog

# class Command(BaseCommand):
#     help = 'Fetch data from ONA and store in local database'

#     def handle(self, *args, **options):
#         self.stdout.write(self.style.SUCCESS("Starting ONA data fetch..."))
        
#         ona_client = ONAClient()
#         partner = Partner.objects.first()
        
#         if not partner:
#             self.stdout.write(self.style.ERROR("No partner found in database"))
#             return

#         sync_log = DataSyncLog.objects.create(
#             partner=partner,
#             sync_type='pull',
#             start_time=timezone.now(),
#             status='in_progress'
#         )

#         try:
#             self.stdout.write("Fetching data from ONA...")
#             events_data = ona_client.fetch_dissemination_events()
            
#             total_records = len(events_data)
#             self.stdout.write(self.style.SUCCESS(f"Found {total_records} records to process"))
            
#             processed = 0
#             failed = 0
#             errors = []

#             # Process records with progress indicator
#             for i, event_data in enumerate(events_data, 1):
#                 success, error = process_dissemination_event(event_data, partner)
#                 if success:
#                     processed += 1
#                 else:
#                     failed += 1
#                     errors.append(error)
                
#                 # Show progress every 100 records
#                 if i % 100 == 0:
#                     self.stdout.write(f"Processed {i}/{total_records} records...")

#             # Update sync log
#             sync_log.status = 'success'
#             sync_log.records_processed = processed
#             sync_log.errors = "\n".join(errors) if errors else ""
#             sync_log.end_time = timezone.now()
#             sync_log.save()

#             self.stdout.write(
#                 self.style.SUCCESS(
#                     f"\nSync completed:\n"
#                     f"- Total records: {total_records}\n"
#                     f"- Successfully processed: {processed}\n"
#                     f"- Failed: {failed}"
#                 )
#             )

#         except Exception as e:
#             sync_log.status = 'failed'
#             sync_log.errors = str(e)
#             sync_log.end_time = timezone.now()
#             sync_log.save()
            
#             self.stdout.write(
#                 self.style.ERROR(f"Error during sync: {str(e)}")
#             )

