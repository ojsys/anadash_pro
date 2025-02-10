# dashboard/utils/data_processor.py
from typing import Dict, Tuple
from datetime import datetime
from django.utils import timezone
from ..models import Event, Location, Partner, ParticipantGroup



def process_dissemination_event(event_data: dict) -> Tuple[bool, str]:
    """
    Process a single dissemination event and save to database
    """
    try:
        # Create or get the location
        location, _ = Location.objects.get_or_create(
            hasc1=event_data.get('state', ''),
            hasc2=event_data.get('LGA', ''),
            city=event_data.get('city', ''),
            defaults={
                'hasc1_name': 'state',
                'hasc2_name': 'LGA'
            }
        )

        # Create or update the event
        event, created = Event.objects.update_or_create(
            odk_id=str(event_data['_id']),
            defaults={
                'partner': event_data.get('partner', ''),  # Directly store partner name
                'location': location,
                'title': event_data.get('title', ''),
                'event_type': event_data.get('event', 'training_event'),
                'format': event_data.get('format', 'paper'),
                'start_date': datetime.strptime(event_data['today'], '%Y-%m-%d').date(),
                'end_date': datetime.strptime(event_data['today'], '%Y-%m-%d').date(),
                'venue': event_data.get('venue', ''),
                'topics': event_data.get('topics', ''),
                'odk_uuid': event_data.get('_uuid', ''),
                'submission_time': datetime.strptime(event_data['_submission_time'], '%Y-%m-%dT%H:%M:%S')
            }
        )

        # Process participant counts if available
        if 'participantDetails' in event_data:
            for group in event_data['participantDetails']:
                participant_type = group.get('participantDetails/participant', '')
                ParticipantGroup.objects.update_or_create(
                    event=event,
                    participant_type=participant_type,
                    defaults={
                        'male_count': int(group.get('participantDetails/participant_male', 0)),
                        'female_count': int(group.get('participantDetails/participant_female', 0))
                    }
                )

        return True, None
    except Exception as e:
        return False, str(e)