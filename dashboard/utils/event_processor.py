from datetime import datetime
from django.utils.timezone import make_aware
from ..models import AkilimoEvent
import logging

logger = logging.getLogger(__name__)

class EventProcessor:
    @staticmethod
    def process_event(event_data: dict) -> tuple[bool, str]:
        try:
            event_id = event_data.get('_id')
            
            # Get or create the event
            event, created = AkilimoEvent.objects.get_or_create(
                odk_id=str(event_id),
                defaults={'odk_uuid': event_data.get('_uuid', None)}
            )

            # Extract geolocation with null handling
            geolocation = event_data.get('_geolocation', [])
            latitude = geolocation[0] if len(geolocation) > 0 else None
            longitude = geolocation[1] if len(geolocation) > 1 else None

            # Process dates with null handling
            try:
                submission_time = make_aware(datetime.strptime(
                    event_data.get('_submission_time'),
                    '%Y-%m-%dT%H:%M:%S'
                )) if event_data.get('_submission_time') else None
            except (ValueError, TypeError):
                submission_time = None

            try:
                start_date = datetime.strptime(
                    event_data.get('dateDetails/startdate', ''),
                    '%Y-%m-%d'
                ).date() if event_data.get('dateDetails/startdate') else None
            except (ValueError, TypeError):
                start_date = None

            # Update event fields with explicit null handling
            field_updates = {
                'submission_time': submission_time,
                'submitted_by': event_data.get('_submitted_by', None),
                'event_type': event_data.get('event', None),
                'partner': event_data.get('partner', None),
                'title': event_data.get('title', None),
                'title_full': event_data.get('topicsDetails', None),
                'format': event_data.get('format', None),
                'topics': event_data.get('topics', None),
                'use_case': event_data.get('useCase', None),
                'image': event_data.get('image', None),
                'city': event_data.get('city', None),
                'hasc1': event_data.get('state', None),
                'hasc2': event_data.get('LGA', None),
                'hasc1_name': event_data.get('state', None),
                'hasc2_name': event_data.get('city', None),
                'venue': event_data.get('venue', None),
                'latitude': latitude,
                'longitude': longitude,
                'event_date': start_date,
                'start_date': start_date,
                'end_date': start_date,
                'enumerator_first_name': event_data.get('respondent/firstNameEN', None),
                'enumerator_surname': event_data.get('respondent/surNameEN', None),
                'enumerator_gender': event_data.get('respondent/genderEN', None),
                'enumerator_phone': event_data.get('respondent/phoneNrEN', None),
                'enumerator_organization': event_data.get('orgEN_other', None),
                'enumerator_designation': event_data.get('respondent/designationEN', None),
                'participantRepeat': event_data.get('participantDetails', []),
                'participantRepeat_count': int(event_data.get('participantDetails_count', 0)),
                'complementary_services': event_data.get('FR', None),
                'input_types': event_data.get('IC', None),
                'input_organizations': event_data.get('SPHS', None),
                'remarks': f"Duration: {event_data.get('duration', '')}\nDevice ID: {event_data.get('deviceid', '')}"
            }

            # Update all fields at once
            for field, value in field_updates.items():
                setattr(event, field, value)

            event.save()
            
            action = "Created" if created else "Updated"
            logger.info(f"{action} event {event_id}")
            return True, f"Event {event_id} {action.lower()} successfully"

        except Exception as e:
            error_msg = f"Error processing event {event_data.get('_id')}: {str(e)}\nData: {event_data}"
            logger.error(error_msg)
            return False, error_msg