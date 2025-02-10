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

    def fetch_dissemination_events(self) -> List[Dict]:
        """
        Fetch all dissemination events from ONA, handling pagination
        """
        base_url = f"{self.base_url}/data/395361"
        all_data = []
        page = 1
        per_page = 1000  # Number of records per page

        while True:
            try:
                print(f"Fetching page {page}...")
                params = {
                    'page': page,
                    'per_page': per_page,
                    'sort': {'_id': 1}  # Sort by ID to ensure consistent pagination
                }
                
                response = requests.get(base_url, headers=self.headers, params=params)
                response.raise_for_status()
                
                # Get current page data
                current_data = response.json()
                
                # If no data returned, we've reached the end
                if not current_data:
                    break

                all_data.extend(current_data)
                records_so_far = len(all_data)
                print(f"Fetched {len(current_data)} records. Total records so far: {records_so_far}")

                # Check if we've reached the end by looking at the returned count
                if len(current_data) < per_page:
                    print("Reached last page")
                    break

                # Add a small delay to avoid overwhelming the API
                time.sleep(1)
                page += 1

            except requests.exceptions.RequestException as e:
                print(f"Error fetching page {page}: {e}")
                if hasattr(e.response, 'text'):
                    print(f"Response content: {e.response.text}")
                break

        print(f"Completed fetching data. Total records fetched: {len(all_data)}")
        return all_data