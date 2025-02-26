# dashboard/integrations/data_processors.py
from typing import Dict, List, Optional
from django.core.exceptions import ValidationError
from django.utils import timezone
from ..models import (
    Partner, Event, Location, Participant, ExtensionAgent, 
    Farmer, ScalingChecklist, ParticipantGroup
)
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class DataValidator:
    """Base validator for ODK data"""
    
    @staticmethod
    def validate_required_fields(data: Dict, required_fields: List[str]):
        """Validate presence of required fields"""
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")

    @staticmethod
    def validate_date_format(date_str: str) -> bool:
        """Validate date string format"""
        try:
            pd.to_datetime(date_str)
            return True
        except:
            return False

class EventProcessor(DataValidator):
    """Process AKILIMO and Dissemination events"""
    REQUIRED_FIELDS = [
        '_id', '_uuid', 'eventDetails/event', 
        'eventLocation/startdate', 'eventLocation/hasc1'
    ]
    
    def __init__(self, partner: Partner):
        self.partner = partner

    def validate(self, data: Dict):
        """Validate event data"""
        self.validate_required_fields(data, self.REQUIRED_FIELDS)
        
        # Validate dates
        if not self.validate_date_format(data['eventLocation/startdate']):
            raise ValidationError("Invalid start date format")
        if 'eventLocation/enddate' in data and not self.validate_date_format(data['eventLocation/enddate']):
            raise ValidationError("Invalid end date format")

    def process(self, data: Dict) -> Event:
        """Process and save event data"""
        try:
            self.validate(data)
            
            # Process location
            location = self._process_location(data)
            
            # Create or update event
            event = self._create_update_event(data, location)
            
            # Process participant groups if present
            if 'participantRepeat' in data:
                self._process_participant_groups(event, data['participantRepeat'])
            
            return event
            
        except Exception as e:
            logger.error(f"Error processing event {data.get('_id')}: {str(e)}")
            raise

    def _process_location(self, data: Dict) -> Location:
        """Process and save location data"""
        return Location.objects.get_or_create(
            hasc1=data['eventLocation/hasc1'],
            hasc2=data.get('eventLocation/hasc2', ''),
            city=data.get('eventLocation/city', ''),
            defaults={
                'hasc1_name': data.get('eventLocation/hasc1_name', ''),
                'hasc2_name': data.get('eventLocation/hasc2_name', '')
            }
        )[0]

    def _create_update_event(self, data: Dict, location: Location) -> Event:
        """Create or update event record"""
        event_data = {
            'location': location,
            'title': data.get('contentDetails/title', ''),
            'event_type': data['eventDetails/event'],
            'start_date': data['eventLocation/startdate'],
            'end_date': data.get('eventLocation/enddate', data['eventLocation/startdate']),
            'venue': data.get('eventLocation/venue', ''),
            'submission_time': data['_submission_time'],
            'odk_uuid': data['_uuid']
        }
        
        event, _ = Event.objects.update_or_create(
            odk_id=data['_id'],
            partner=self.partner,
            defaults=event_data
        )
        
        return event

    def _process_participant_groups(self, event: Event, groups_data: List[Dict]):
        """Process participant group counts"""
        for group in groups_data:
            ParticipantGroup.objects.update_or_create(
                event=event,
                participant_type=group.get('participant', 'unknown'),
                defaults={
                    'male_count': int(group.get('participant_male', 0)),
                    'female_count': int(group.get('participant_female', 0))
                }
            )

class ParticipantProcessor(DataValidator):
    """Process participant data from various forms"""
    REQUIRED_FIELDS = ['_id', '_uuid', 'repeatPP']

    def __init__(self, partner: Partner):
        self.partner = partner

    def validate(self, data: Dict):
        """Validate participant data"""
        self.validate_required_fields(data, self.REQUIRED_FIELDS)
        
        if not isinstance(data['repeatPP'], list):
            raise ValidationError("repeatPP must be a list")

    def process(self, data: Dict) -> List[Participant]:
        """Process and save participant data"""
        try:
            self.validate(data)
            
            participants = []
            event = self._get_event(data)
            
            for participant_data in data['repeatPP']:
                participant = self._create_update_participant(participant_data, event)
                participants.append(participant)
            
            return participants
            
        except Exception as e:
            logger.error(f"Error processing participants for {data.get('_id')}: {str(e)}")
            raise

    def _get_event(self, data: Dict) -> Optional[Event]:
        """Get associated event if exists"""
        event_uuid = data.get('eventDetails/uuid_event')
        if event_uuid:
            return Event.objects.filter(odk_uuid=event_uuid).first()
        return None

    def _create_update_participant(self, data: Dict, event: Optional[Event]) -> Participant:
        """Create or update participant record"""
        participant_data = {
            'first_name': data.get('repeatPP/firstNamePP', '').strip(),
            'surname': data.get('repeatPP/surNamePP', '').strip(),
            'gender': data.get('repeatPP/genderPP', ''),
            'phone_number': data.get('repeatPP/phoneNrPP'),
            'own_phone': data.get('repeatPP/ownPhonePP') == 'yes',
            'has_whatsapp': data.get('repeatPP/whatsAppPP') == 'yes',
            'partner': self.partner,
            'event': event
        }
        
        participant, _ = Participant.objects.update_or_create(
            odk_id=f"{data.get('_id')}_{participant_data['phone_number']}",
            defaults=participant_data
        )
        
        return participant


class ExtensionAgentProcessor(DataValidator):
    """Process Extension Agent registrations"""
    REQUIRED_FIELDS = [
        '_id', '_uuid', 'detailsEA/firstName', 'detailsEA/surName',
        'detailsEA/gender', 'detailsEA/phoneNr', 'detailsEA/org'
    ]

    def __init__(self, partner: Partner):
        self.partner = partner

    def validate(self, data: Dict):
        """Validate EA data"""
        self.validate_required_fields(data, self.REQUIRED_FIELDS)
        
        # Validate states if present
        if 'areaOperation/hasc1' in data:
            states = data['areaOperation/hasc1'].split()
            if not all(state.startswith(('NG.', 'TZ.')) for state in states):
                raise ValidationError("Invalid state codes format")

    def process(self, data: Dict) -> ExtensionAgent:
        """Process and save extension agent data"""
        try:
            self.validate(data)
            
            # Create base participant record
            participant = self._create_participant(data)
            
            # Create or update EA record
            ea_data = {
                'participant': participant,
                'designation': data.get('detailsEA/designation', ''),
                'education_level': data.get('detailsEA/education', ''),
                'organization': data['detailsEA/org'],
                'organization_type': data.get('detailsEA/type', ''),
                'operational_level': data.get('areaOperation/areaLevel', ''),
                'number_of_farmers': int(data.get('areaOperation/nrFarmers', 0)),
                'states': data.get('areaOperation/hasc1', '').split(),
                'akilimo_tools': data.get('AKILIMOexpertise/tools', '').split(),
                'akilimo_formats': data.get('AKILIMOexpertise/format', '').split(),
                'akilimo_use_cases': data.get('AKILIMOexpertise/useCase', '').split(),
                'is_akilimo_certified': data.get('AKILIMOexpertise/certified') == 'yes',
                'crops': data.get('otherExpertise/crops', '').split(),
                'technologies': data.get('otherExpertise/technologies', '').split()
            }
            
            ea, _ = ExtensionAgent.objects.update_or_create(
                participant=participant,
                defaults=ea_data
            )
            
            return ea
            
        except Exception as e:
            logger.error(f"Error processing EA {data.get('_id')}: {str(e)}")
            raise

    def _create_participant(self, data: Dict) -> Participant:
        """Create base participant record for EA"""
        participant_data = {
            'first_name': data['detailsEA/firstName'].strip(),
            'surname': data['detailsEA/surName'].strip(),
            'gender': data['detailsEA/gender'],
            'phone_number': data['detailsEA/phoneNr'],
            'email': data.get('detailsEA/email'),
            'own_phone': True,  # Assumed for EAs
            'has_whatsapp': data.get('detailsEA/whatsApp') == 'yes',
            'partner': self.partner
        }
        
        participant, _ = Participant.objects.update_or_create(
            odk_id=data['_id'],
            defaults=participant_data
        )
        
        return participant

class FarmerProcessor(DataValidator):
    """Process Farmer self-registrations"""
    REQUIRED_FIELDS = [
        '_id', '_uuid', 'farmerDetails/firstNamePP', 'farmerDetails/surNamePP',
        'farmerDetails/genderPP', 'farmerDetails/farmAreaPP'
    ]

    def __init__(self, partner: Partner):
        self.partner = partner

    def validate(self, data: Dict):
        """Validate farmer data"""
        self.validate_required_fields(data, self.REQUIRED_FIELDS)
        
        # Validate farm area
        try:
            float(data['farmerDetails/farmAreaPP'])
        except ValueError:
            raise ValidationError("Invalid farm area value")

    def process(self, data: Dict) -> Farmer:
        """Process and save farmer data"""
        try:
            self.validate(data)
            
            # Create location
            location = self._process_location(data)
            
            # Create base participant record
            participant = self._create_participant(data)
            
            # Create or update farmer record
            farmer_data = {
                'participant': participant,
                'farm_area': float(data['farmerDetails/farmAreaPP']),
                'area_unit': data['farmerDetails/area_unit'],
                'location': location,
                'crops': data.get('farmerDetails/cropsPP', '').split(),
                'other_crops': data.get('farmerDetails/cropsPP_other', ''),
                'consent_given_for': data.get('farmerDetails/consent', '').split(),
                'registration_source': data['sourceDetails/source'],
                'registration_date': data['sourceDetails/startdate']
            }
            
            farmer, _ = Farmer.objects.update_or_create(
                participant=participant,
                defaults=farmer_data
            )
            
            return farmer
            
        except Exception as e:
            logger.error(f"Error processing farmer {data.get('_id')}: {str(e)}")
            raise

    def _process_location(self, data: Dict) -> Location:
        """Process and save location data"""
        return Location.objects.get_or_create(
            hasc1=data['farmerDetails/hasc1'],
            hasc2=data['farmerDetails/hasc2'],
            city=data['farmerDetails/city'],
            defaults={
                'hasc1_name': data.get('farmerDetails/hasc1_name', ''),
                'hasc2_name': data.get('farmerDetails/hasc2_name', '')
            }
        )[0]

class ScalingChecklistProcessor(DataValidator):
    """Process Scaling Checklist submissions"""
    REQUIRED_FIELDS = [
        '_id', '_uuid', 'Core_business', 'target_group',
        'main_target_group'
    ]

    def __init__(self, partner: Partner):
        self.partner = partner

    def process(self, data: Dict) -> ScalingChecklist:
        """Process and save scaling checklist data"""
        try:
            self.validate(data)
            
            checklist_data = {
                'partner': self.partner,
                'submission_date': data['_submission_time'],
                'main_business': data['main_business'],
                'core_business': data['Core_business'],
                'target_groups': data['target_group'].split(),
                'main_target_group': data['main_target_group'],
                'knows_akilimo': data['knowAKILIMO'] == 'yes',
                'akilimo_relevant': data['AKILIMORelevant'] == 'yes',
                'use_cases': data['useCase'].split(),
                'integration_type': data.get('Integration/support', ''),
                'has_mel_system': True if data.get('MEL/system') else False,
                'system_type': data.get('MEL/system', ''),
                'collects_data': data.get('MEL/data_collection') == 'yes',
                'has_farmer_database': data.get('MEL/farmers_database') == 'yes',
                'has_agrodealer_database': data.get('MEL/agrodealers_database') == 'yes',
                'odk_id': data['_id'],
                'odk_uuid': data['_uuid']
            }
            
            checklist, _ = ScalingChecklist.objects.update_or_create(
                odk_id=data['_id'],
                defaults=checklist_data
            )
            
            return checklist
            
        except Exception as e:
            logger.error(f"Error processing checklist {data.get('_id')}: {str(e)}")
            raise


class PartnerProcessor(DataValidator):
    def process(self, data: dict):
        """Process partner data from ODK"""
        try:
            # Extract location data if present
            location_data = data.get('location', {})
            location = None
            if location_data:
                location, _ = Location.objects.get_or_create(
                    latitude=location_data.get('latitude'),
                    longitude=location_data.get('longitude'),
                    defaults={
                        'country': data.get('country'),
                        'region': location_data.get('region'),
                        'district': location_data.get('district')
                    }
                )

            # Process partner data
            partner_data = {
                'name': data.get('name'),
                'country': data.get('country'),
                'organization_type': data.get('org_type'),
                'contact_person': data.get('contact_person'),
                'contact_email': data.get('contact_email'),
                'contact_phone': data.get('contact_phone'),
                'is_active': data.get('is_active', True),
                'location': location,
                'last_sync': timezone.now()
            }

            # Update or create partner
            partner, created = Partner.objects.update_or_create(
                odk_id=data.get('_id'),
                defaults=partner_data
            )

            return partner

        except Exception as e:
            logger.error(f"Error processing partner data: {str(e)}")
            raise