from typing import Dict
from .ona_client import ONAClient
from .data_processor import (
    process_dissemination_event,
    process_participant,
    process_extension_agent,
    process_farmer,
    process_scaling_checklist
)
import logging

logger = logging.getLogger(__name__)

class SyncOrchestrator:
    def __init__(self):
        self.client = ONAClient()
        
    def sync_all_data(self) -> Dict:
        """Synchronize all data types from ONA"""
        results = {
            'events': self._sync_events(),
            'extension_agents': self._sync_extension_agents(),
            'farmers': self._sync_farmers(),
            'checklists': self._sync_checklists()
        }
        return results

    def _sync_events(self) -> Dict:
        """Sync dissemination events"""
        try:
            events_data = self.client.fetch_dissemination_events()
            processed = 0
            errors = []
            
            for event in events_data:
                success, error = process_dissemination_event(event)
                if success:
                    processed += 1
                else:
                    errors.append(error)
            
            return {
                'total': len(events_data),
                'processed': processed,
                'errors': errors
            }
        except Exception as e:
            logger.error(f"Error syncing events: {str(e)}")
            return {'error': str(e)}

    def _sync_extension_agents(self) -> Dict:
        """Sync extension agents"""
        try:
            agents_data = self.client.fetch_extension_agents()  # You'll need to implement this
            processed = 0
            errors = []
            
            for agent in agents_data:
                success, error = process_extension_agent(agent)
                if success:
                    processed += 1
                else:
                    errors.append(error)
            
            return {
                'total': len(agents_data),
                'processed': processed,
                'errors': errors
            }
        except Exception as e:
            logger.error(f"Error syncing extension agents: {str(e)}")
            return {'error': str(e)}

    def _sync_farmers(self) -> Dict:
        """Sync farmers"""
        try:
            farmers_data = self.client.fetch_farmers()  # You'll need to implement this
            processed = 0
            errors = []
            
            for farmer in farmers_data:
                success, error = process_farmer(farmer)
                if success:
                    processed += 1
                else:
                    errors.append(error)
            
            return {
                'total': len(farmers_data),
                'processed': processed,
                'errors': errors
            }
        except Exception as e:
            logger.error(f"Error syncing farmers: {str(e)}")
            return {'error': str(e)}

    def _sync_checklists(self) -> Dict:
        """Sync scaling checklists"""
        try:
            checklists_data = self.client.fetch_checklists()  # You'll need to implement this
            processed = 0
            errors = []
            
            for checklist in checklists_data:
                success, error = process_scaling_checklist(checklist)
                if success:
                    processed += 1
                else:
                    errors.append(error)
            
            return {
                'total': len(checklists_data),
                'processed': processed,
                'errors': errors
            }
        except Exception as e:
            logger.error(f"Error syncing checklists: {str(e)}")
            return {'error': str(e)}