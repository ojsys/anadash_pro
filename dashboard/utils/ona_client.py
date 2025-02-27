import requests
from typing import Dict, List
from django.conf import settings
import time

class ONAClient:
    def __init__(self):
        self.base_url = "https://api.ona.io/api/v1"
        self.token = settings.ONA_API_TOKEN
        self.headers = {
            "Authorization": f"Token {self.token}", 
            "Content-Type": "application/json"
        }
        # Form IDs for different data types
        self.FORM_IDS = {
            'events': '395361',
            'extension_agents': '765372',  
            'participants': '395362',  
            'checklists': '627778'  
        }

    def _fetch_paginated_data(self, form_id: str) -> List[Dict]:
        """Generic method to fetch paginated data from any form"""
        base_url = f"{self.base_url}/data/{form_id}"
        all_data = []
        page = 1
        per_page = 1000

        while True:
            try:
                print(f"Fetching {form_id} page {page}...")
                params = {
                    'page': page,
                    'per_page': per_page,
                    'sort': {'_id': 1}
                }
                
                response = requests.get(base_url, headers=self.headers, params=params)
                response.raise_for_status()
                
                current_data = response.json()
                if not current_data:
                    break

                all_data.extend(current_data)
                print(f"Fetched {len(current_data)} records. Total: {len(all_data)}")

                if len(current_data) < per_page:
                    print("Reached last page")
                    break

                time.sleep(1)
                page += 1

            except requests.exceptions.RequestException as e:
                print(f"Error fetching page {page}: {e}")
                if hasattr(e.response, 'text'):
                    print(f"Response content: {e.response.text}")
                break

        print(f"Completed fetching {form_id}. Total records: {len(all_data)}")
        return all_data


    def fetch_dissemination_events(self) -> List[Dict]:
        """Fetch all dissemination events"""
        return self._fetch_paginated_data(self.FORM_IDS['events'])

    def fetch_participants(self) -> List[Dict]:
        """Fetch all participants data"""
        return self._fetch_paginated_data(self.FORM_IDS['participants'])

    def fetch_extension_agents(self) -> List[Dict]:
        """Fetch all extension agents data"""
        return self._fetch_paginated_data(self.FORM_IDS['extension_agents'])


    def fetch_checklists(self) -> List[Dict]:
        """Fetch all scaling checklists"""
        return self._fetch_paginated_data(self.FORM_IDS['checklists'])