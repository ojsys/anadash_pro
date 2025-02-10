import requests
import json
import logging
from typing import Dict, List, Optional, Union
from datetime import datetime
from django.conf import settings

logger = logging.getLogger(__name__)

class ODKAPIClient:
    """
    Client for interacting with ODK API
    """
    def __init__(self, api_key: str):
        self.base_url = "https://api.ona.io/api/v1"
        self.headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json"
        }
        
        # Form IDs mapping
        self.FORM_IDS = {
            'events': '763697',                    # AKILIMO Events
            'participants': '763725',              # AKILIMO Participants
            'extension_agents': '765372',          # AKILIMO EAs
            'farmer_registration': '765230',       # Farmer Self Registration
            'scaling_checklist': '627778',         # Scaling Checklist
            'dissemination_events': '395361',      # ACAI Dissemination Events
            'participants_upload': '395362'        # Dissemination Events Participant Upload
        }

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request to ODK API with error handling"""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"ODK API request failed: {str(e)}")
            raise

    def get_form_data(self, form_id: str, last_sync: Optional[datetime] = None) -> List[Dict]:
        """Fetch form submissions from ODK"""
        params = {}
        if last_sync:
            params['query'] = json.dumps({
                "_submission_time": {
                    "$gt": last_sync.isoformat()
                }
            })
        
        response = self._make_request("GET", f"data/{form_id}", params=params)
        return response.json()

    def get_form_attachments(self, form_id: str, submission_id: str) -> List[Dict]:
        """Fetch attachments for a specific submission"""
        response = self._make_request("GET", f"data/{form_id}/{submission_id}/attachments")
        return response.json()

    def download_attachment(self, attachment_url: str) -> bytes:
        """Download a specific attachment"""
        response = self._make_request("GET", attachment_url, stream=True)
        return response.content

    def submit_form_data(self, form_id: str, data: Dict) -> Dict:
        """Submit form data to ODK"""
        return self._make_request("POST", f"data/{form_id}", json=data).json()