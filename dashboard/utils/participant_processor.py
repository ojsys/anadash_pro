from datetime import datetime
from django.utils.timezone import make_aware
from ..models import Participant, Partner, Event
import logging

logger = logging.getLogger(__name__)

class ParticipantProcessor:
    @staticmethod
    def process_participants(event_data: dict) -> tuple[bool, str]:
        try:
            # Get partner
            partner_name = event_data.get('eventDetails/partner')
            partner = Partner.objects.get_or_create(name=partner_name)[0]

            # Get or create event
            event_id = f"{partner_name}_{event_data.get('eventDetails/event')}_{event_data.get('eventLocation/hasc2')}_{event_data.get('eventLocation/startdate')}"
            event = Event.objects.filter(title=event_data.get('contentDetails/title_manual')).first()

            # Process submission time with timezone handling
            try:
                submission_time = datetime.strptime(
                    event_data.get('_submission_time').split('.')[0],  # Remove milliseconds
                    '%Y-%m-%dT%H:%M:%S'
                )
                submission_time = make_aware(submission_time)
            except (ValueError, AttributeError):
                submission_time = timezone.now()  # Fallback to current time if parsing fails

            # Process participants from repeatPP
            participants_data = event_data.get('repeatPP', [])
            processed = 0
            errors = []

            for participant_data in participants_data:
                try:
                    participant = Participant(
                        partner=partner,
                        event=event,
                        first_name=participant_data.get('repeatPP/firstNamePP', '').strip(),
                        surname=participant_data.get('repeatPP/surNamePP', '').strip(),
                        gender=participant_data.get('repeatPP/genderPP'),
                        phone_number=participant_data.get('repeatPP/phoneNrPP'),
                        own_phone=participant_data.get('repeatPP/ownPhonePP') == 'yes',
                        has_whatsapp=False,  # Default value as it's not in the data
                        odk_id=str(event_data.get('_id')),
                        submission_time=submission_time
                    )
                    participant.save()
                    processed += 1

                    # Create Farmer record if farm area exists
                    farm_area = participant_data.get('repeatPP/farmAreaPP')
                    if farm_area:
                        from ..models import Farmer, Location
                        location = Location.objects.get_or_create(
                            hasc1=event_data.get('eventLocation/hasc1'),
                            hasc1_name=event_data.get('eventLocation/hasc1_name'),
                            hasc2=event_data.get('eventLocation/hasc2'),
                            hasc2_name=event_data.get('eventLocation/hasc2_name'),
                            city=event_data.get('eventLocation/city', '')
                        )[0]

                        Farmer.objects.create(
                            participant=participant,
                            farm_area=float(farm_area),
                            area_unit=event_data.get('contentDetails/area_unit', 'acre'),
                            location=location,
                            crops=participant_data.get('repeatPP/cropsPP', '').split(),
                            consent_given_for=[event_data.get('contentDetails/consent')] if event_data.get('contentDetails/consent') else [],
                            registration_source='event_registration',
                            registration_date=datetime.strptime(event_data.get('eventLocation/startdate'), '%Y-%m-%d').date()
                        )

                except Exception as e:
                    errors.append(f"Error processing participant {participant_data.get('repeatPP/firstNamePP')} {participant_data.get('repeatPP/surNamePP')}: {str(e)}")

            return True, f"Processed {processed} participants. Errors: {len(errors)}"

        except Exception as e:
            error_msg = f"Error processing participants: {str(e)}"
            logger.error(error_msg)
            return False, error_msg