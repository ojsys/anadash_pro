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
    def __init__(self, partner: Partner):
        self.partner = partner
        self.api_client = ODKAPIClient(partner.api_key)
        self.sync_log = None

    def _start_sync_log(self, sync_type: str):
        self.sync_log = DataSyncLog.objects.create(
            partner=self.partner,
            sync_type=sync_type,
            start_time=timezone.now()
        )

    def _end_sync_log(self, status: str, records_processed: int, errors: List[str] = None):
        if self.sync_log:
            self.sync_log.end_time = timezone.now()
            self.sync_log.status = status
            self.sync_log.records_processed = records_processed
            if errors:
                self.sync_log.errors = "\n".join(errors)
            self.sync_log.save()

    def _create_sync_status(self, form_type: str) -> DataSyncStatus:
        return DataSyncStatus.objects.create(
            partner=self.partner,
            form_type=form_type,
            status='in_progress'
        )

    def _update_sync_status(self, sync_status: DataSyncStatus, status: str, 
                           processed: int, failed: int, error_message: str = None):
        sync_status.status = status
        sync_status.records_processed = processed
        sync_status.records_failed = failed
        sync_status.error_message = error_message
        sync_status.completed_at = timezone.now()
        sync_status.save()

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
    def sync_to_odk(self, form_type: str, local_data: List[Dict]) -> Dict:
        """Push updates from dashboard to ODK"""
        sync_status = self._create_sync_status(form_type)
        self._start_sync_log(f'push_{form_type}')
        
        sync_results = {
            'submitted': 0,
            'failed': 0,
            'errors': []
        }

        try:
            form_id = self.api_client.FORM_IDS.get(form_type)
            if not form_id:
                raise ValueError(f"Invalid form type: {form_type}")

            for data in local_data:
                try:
                    self.api_client.submit_form_data(form_id, data)
                    sync_results['submitted'] += 1
                except Exception as e:
                    sync_results['failed'] += 1
                    sync_results['errors'].append(str(e))

            status = 'success' if not sync_results['errors'] else 'partial'
            self._end_sync_log(status, sync_results['submitted'], sync_results['errors'])
            self._update_sync_status(
                sync_status, 
                status,
                sync_results['submitted'],
                sync_results['failed']
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Push sync failed: {error_msg}")
            sync_results['errors'].append(error_msg)
            self._end_sync_log('failed', sync_results['submitted'], sync_results['errors'])
            self._update_sync_status(
                sync_status,
                'failed',
                sync_results['submitted'],
                sync_results['failed'],
                error_msg
            )

        return sync_results

    def sync_all_to_odk(self) -> Dict:
        """Sync all data types to ODK"""
        results = {}
        
        for form_type in ['partners', 'events', 'participants', 'extension_agents', 'farmers', 'checklists']:
            try:
                method = getattr(self, f'sync_{form_type}_to_odk')
                results[form_type] = method()
            except Exception as e:
                logger.error(f"Error syncing {form_type}: {str(e)}")
                results[form_type] = {
                    'status': 'failed',
                    'error': str(e)
                }
        
        return results

    def sync_partners_to_odk(self) -> Dict:
        partners = Partner.objects.filter(needs_sync=True)
        data = [partner.to_odk_format() for partner in partners]
        return self.sync_to_odk('partners', data)

    def sync_events_to_odk(self) -> Dict:
        events = Event.objects.filter(partner=self.partner, needs_sync=True)
        data = [event.to_odk_format() for event in events]
        return self.sync_to_odk('events', data)

    def sync_participants_to_odk(self) -> Dict:
        participants = Participant.objects.filter(partner=self.partner, needs_sync=True)
        data = [participant.to_odk_format() for participant in participants]
        return self.sync_to_odk('participants', data)

    def sync_extension_agents_to_odk(self) -> Dict:
        agents = ExtensionAgent.objects.filter(participant__partner=self.partner, needs_sync=True)
        data = [agent.to_odk_format() for agent in agents]
        return self.sync_to_odk('extension_agents', data)

    def sync_farmers_to_odk(self) -> Dict:
        farmers = Farmer.objects.filter(participant__partner=self.partner, needs_sync=True)
        data = [farmer.to_odk_format() for farmer in farmers]
        return self.sync_to_odk('farmers', data)

    def sync_checklists_to_odk(self) -> Dict:
        checklists = ScalingChecklist.objects.filter(partner=self.partner, needs_sync=True)
        data = [checklist.to_odk_format() for checklist in checklists]
        return self.sync_to_odk('checklists', data)