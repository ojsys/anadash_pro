from django.db import transaction
from django.utils import timezone
from typing import Dict, List, Optional
import logging
from ..models import (
    Partner, Event, Participant, ExtensionAgent, 
    Farmer, ScalingChecklist, Location, DataSyncLog,
    EventAttachment, ParticipantGroup, DataSyncStatus
)
from .odk_client import ODKAPIClient
from .data_processors import (
    EventProcessor, ParticipantProcessor, 
    ExtensionAgentProcessor, FarmerProcessor,
    ScalingChecklistProcessor, PartnerProcessor
)

logger = logging.getLogger(__name__)

class DataSyncManager:
    """
    Manages data synchronization between dashboard and ODK
    """
    def __init__(self, partner: Partner):
        self.partner = partner
        self.api_client = ODKAPIClient(partner.api_key)
        self.sync_log = None

    def _start_sync_log(self, sync_type: str):
        """Initialize sync log entry"""
        self.sync_log = DataSyncLog.objects.create(
            partner=self.partner,
            sync_type=sync_type,
            start_time=timezone.now()
        )

    def _end_sync_log(self, status: str, records_processed: int, errors: List[str] = None):
        """Complete sync log entry"""
        if self.sync_log:
            self.sync_log.end_time = timezone.now()
            self.sync_log.status = status
            self.sync_log.records_processed = records_processed
            if errors:
                self.sync_log.errors = "\n".join(errors)
            self.sync_log.save()

    @transaction.atomic
    def sync_from_odk(self) -> Dict:
        """Pull updates from ODK to dashboard"""
        self._start_sync_log('pull')
        
        sync_results = {
            'partners': 0,
            'events': 0,
            'participants': 0,
            'extension_agents': 0,
            'farmers': 0,
            'checklists': 0,
            'errors': []
        }

        try:
            # Sync Partners first
            partners_data = self.api_client.get_form_data(
                self.api_client.FORM_IDS['partners'],
                self.partner.last_sync
            )
            processor = PartnerProcessor(self.partner)
            for partner_data in partners_data:
                try:
                    processor.process(partner_data)
                    sync_results['partners'] += 1
                except Exception as e:
                    sync_results['errors'].append(f"Partner sync error: {str(e)}")

            # Sync Events
            events_data = self.api_client.get_form_data(
                self.api_client.FORM_IDS['events'],
                self.partner.last_sync
            )
            processor = EventProcessor(self.partner)
            for event_data in events_data:
                try:
                    processor.process(event_data)
                    sync_results['events'] += 1
                except Exception as e:
                    sync_results['errors'].append(f"Event sync error: {str(e)}")

            # Sync Participants
            participants_data = self.api_client.get_form_data(
                self.api_client.FORM_IDS['participants'],
                self.partner.last_sync
            )
            processor = ParticipantProcessor(self.partner)
            for participant_data in participants_data:
                try:
                    processor.process(participant_data)
                    sync_results['participants'] += 1
                except Exception as e:
                    sync_results['errors'].append(f"Participant sync error: {str(e)}")

            # Sync Extension Agents
            agents_data = self.api_client.get_form_data(
                self.api_client.FORM_IDS['extension_agents'],
                self.partner.last_sync
            )
            processor = ExtensionAgentProcessor(self.partner)
            for agent_data in agents_data:
                try:
                    processor.process(agent_data)
                    sync_results['extension_agents'] += 1
                except Exception as e:
                    sync_results['errors'].append(f"Extension agent sync error: {str(e)}")

            # Sync Farmers
            farmers_data = self.api_client.get_form_data(
                self.api_client.FORM_IDS['farmers'],
                self.partner.last_sync
            )
            processor = FarmerProcessor(self.partner)
            for farmer_data in farmers_data:
                try:
                    processor.process(farmer_data)
                    sync_results['farmers'] += 1
                except Exception as e:
                    sync_results['errors'].append(f"Farmer sync error: {str(e)}")

            # Sync Scaling Checklists
            checklist_data = self.api_client.get_form_data(
                self.api_client.FORM_IDS['checklists'],
                self.partner.last_sync
            )
            processor = ScalingChecklistProcessor(self.partner)
            for checklist_item in checklist_data:
                try:
                    processor.process(checklist_item)
                    sync_results['checklists'] += 1
                except Exception as e:
                    sync_results['errors'].append(f"Checklist sync error: {str(e)}")

            # Update last sync time and save results
            self.partner.last_sync = timezone.now()
            self.partner.save()

            status = 'success' if not sync_results['errors'] else 'partial'
            total_records = sum(v for k, v in sync_results.items() if k != 'errors')
            self._end_sync_log(status, total_records, sync_results['errors'])

        except Exception as e:
            logger.error(f"Sync failed for partner {self.partner.name}: {str(e)}")
            sync_results['errors'].append(f"Global sync error: {str(e)}")
            self._end_sync_log('failed', 0, sync_results['errors'])

        return sync_results



    @transaction.atomic
    def sync_to_odk(self, form_id: str, local_data: List[Dict]) -> Dict:
        """Push updates from dashboard to ODK"""
        self._start_sync_log('push')
        
        sync_results = {
            'submitted': 0,
            'failed': 0,
            'errors': []
        }

        try:
            for data in local_data:
                try:
                    self.api_client.submit_form_data(form_id, data)
                    sync_results['submitted'] += 1
                except Exception as e:
                    sync_results['failed'] += 1
                    sync_results['errors'].append(str(e))

            status = 'success' if not sync_results['errors'] else 'partial'
            self._end_sync_log(
                status, 
                sync_results['submitted'], 
                sync_results['errors']
            )

        except Exception as e:
            logger.error(f"Push sync failed: {str(e)}")
            sync_results['errors'].append(str(e))
            self._end_sync_log('failed', sync_results['submitted'], sync_results['errors'])

        return sync_results
    
    def sync_events(self):
        sync_status = DataSyncStatus.objects.create(
            partner=self.partner,
            form_type='events',
            status='in_progress'
        )
        
        try:
            events_data = self.api_client.get_form_data(
                self.api_client.FORM_IDS['events'],
                self.partner.last_sync
            )
            
            records_processed = 0
            records_failed = 0
            
            for event_data in events_data:
                try:
                    # Process event data...
                    records_processed += 1
                except Exception as e:
                    records_failed += 1
                    logger.error(f"Error processing event: {str(e)}")
            
            sync_status.status = 'completed'
            sync_status.records_processed = records_processed
            sync_status.records_failed = records_failed
            sync_status.completed_at = timezone.now()
            sync_status.save()
            
        except Exception as e:
            sync_status.status = 'failed'
            sync_status.error_message = str(e)
            sync_status.completed_at = timezone.now()
            sync_status.save()
            raise

    def sync_partners(self):
        sync_status = DataSyncStatus.objects.create(
            partner=self.partner,
            form_type='partners',
            status='in_progress'
        )
        
        try:
            partners_data = self.api_client.get_form_data(
                self.api_client.FORM_IDS['partners'],
                self.partner.last_sync
            )
            
            records_processed = 0
            records_failed = 0
            
            for partner_data in partners_data:
                try:
                    # Process partner data using the processor
                    processor = PartnerProcessor(self.partner)
                    processor.process(partner_data)
                    records_processed += 1
                except Exception as e:
                    records_failed += 1
                    logger.error(f"Error processing partner: {str(e)}")
            
            sync_status.status = 'completed'
            sync_status.records_processed = records_processed
            sync_status.records_failed = records_failed
            sync_status.completed_at = timezone.now()
            sync_status.save()
            
            return {
                'processed': records_processed,
                'failed': records_failed,
                'status': 'completed'
            }
            
        except Exception as e:
            sync_status.status = 'failed'
            sync_status.error_message = str(e)
            sync_status.completed_at = timezone.now()
            sync_status.save()
            logger.error(f"Partner sync failed: {str(e)}")
            raise

    