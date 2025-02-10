from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from dashboard.models import Partner
from dashboard.integrations.sync_manager import DataSyncManager
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Synchronize data with ODK server'

    def add_arguments(self, parser):
        parser.add_argument(
            '--partner',
            type=str,
            help='Partner ID or "all" for all partners'
        )
        parser.add_argument(
            '--direction',
            type=str,
            choices=['pull', 'push', 'both'],
            default='pull',
            help='Sync direction: pull from ODK, push to ODK, or both'
        )
        parser.add_argument(
            '--form-type',
            type=str,
            choices=['all', 'events', 'participants', 'extension-agents', 'farmers', 'checklist'],
            default='all',
            help='Type of form to sync'
        )

    def handle(self, *args, **options):
        try:
            # Get partners to process
            if options['partner'] == 'all':
                partners = Partner.objects.filter(is_active=True)
            else:
                partners = Partner.objects.filter(
                    id=options['partner'],
                    is_active=True
                )

            if not partners.exists():
                raise CommandError('No active partners found')

            total_results = {
                'processed': 0,
                'errors': 0,
                'partners': 0
            }

            # Process each partner
            for partner in partners:
                self.stdout.write(f"Processing partner: {partner.name}")
                sync_manager = DataSyncManager(partner)

                try:
                    if options['direction'] in ['pull', 'both']:
                        results = sync_manager.sync_from_odk()
                        self._process_results('Pull', results)
                        total_results['processed'] += sum(
                            v for k, v in results.items() 
                            if k != 'errors'
                        )
                        total_results['errors'] += len(results['errors'])

                    if options['direction'] in ['push', 'both']:
                        # Implement push logic based on form type
                        pass

                    total_results['partners'] += 1

                except Exception as e:
                    self.stderr.write(f"Error processing partner {partner.name}: {str(e)}")
                    total_results['errors'] += 1

            # Print summary
            self.stdout.write(self.style.SUCCESS(
                f"\nSync completed:"
                f"\n- Partners processed: {total_results['partners']}"
                f"\n- Records processed: {total_results['processed']}"
                f"\n- Errors encountered: {total_results['errors']}"
            ))

        except Exception as e:
            raise CommandError(f"Sync failed: {str(e)}")

    def _process_results(self, operation: str, results: dict):
        """Process and display sync results"""
        self.stdout.write(f"\n{operation} Results:")
        for key, value in results.items():
            if key != 'errors':
                self.stdout.write(f"- {key.title()}: {value}")
        
        if results['errors']:
            self.stdout.write(self.style.WARNING("\nErrors:"))
            for error in results['errors']:
                self.stdout.write(f"- {error}")