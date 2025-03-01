from django.conf import settings
import requests
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class AkilimoEventFetcher:
    def __init__(self):
        self.api_token = settings.ONA_API_TOKEN
        self.base_url = settings.ODK_API_BASE_URL
        self.form_id = '395361'
        self.timeout = settings.ODK_API_TIMEOUT
        self.page_size = 1000  # Number of records per page

    def fetch_events(self) -> List[Dict]:
        """Fetch all AKILIMO events from ODK with pagination"""
        all_events = []
        page = 1
        
        try:
            while True:
                headers = {
                    'Authorization': f'Token {self.api_token}'
                }
                
                params = {
                    'page': page,
                    'page_size': self.page_size,
                    'format': 'json'
                }
                
                response = requests.get(
                    f'{self.base_url}/data/{self.form_id}',
                    headers=headers,
                    params=params,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    events = response.json()
                    if not events:  # No more records
                        break
                        
                    all_events.extend(events)
                    logger.info(f"Fetched page {page} with {len(events)} events")
                    page += 1
                else:
                    logger.error(f"Failed to fetch page {page}. Status code: {response.status_code}")
                    break
                    
            logger.info(f"Successfully fetched total of {len(all_events)} events from ODK")
            return all_events
                
        except Exception as e:
            logger.error(f"Error fetching events: {str(e)}")
            return []