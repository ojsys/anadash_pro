# dashboard/utils/data_processor.py
from typing import Dict, Tuple
from datetime import datetime
from django.utils import timezone
from ..models import (
    Event, Location, Partner, ParticipantGroup, Participant,
    ExtensionAgent, Farmer, ScalingChecklist
)



def process_dissemination_event(event_data: dict) -> Tuple[bool, str]:
    try:
        # First create or get partner from event data
        partner_name = event_data.get('partner', '')
        if partner_name:
            partner, _ = Partner.objects.get_or_create(
                name=partner_name,
                defaults={'country': 'NG', 'is_active': True}
            )
        
        # Create or get location
        location, _ = Location.objects.get_or_create(
            hasc1=event_data.get('state', ''),
            hasc2=event_data.get('LGA', ''),
            city=event_data.get('city', ''),
            defaults={
                'hasc1_name': 'state',
                'hasc2_name': 'LGA'
            }
        )

        # Make datetime timezone-aware
        submission_time = timezone.make_aware(
            datetime.strptime(event_data['_submission_time'], '%Y-%m-%dT%H:%M:%S')
        )

        # Create or update event with partner relationship
        event, created = Event.objects.update_or_create(
            odk_id=str(event_data['_id']),
            defaults={
                'partner': partner if partner_name else None,
                'location': location,
                'title': event_data.get('title', ''),
                'event_type': event_data.get('event', 'training_event'),
                'format': event_data.get('format', 'paper'),
                'start_date': datetime.strptime(event_data['today'], '%Y-%m-%d').date(),
                'end_date': datetime.strptime(event_data['today'], '%Y-%m-%d').date(),
                'venue': event_data.get('venue', ''),
                'topics': event_data.get('topics', ''),
                'odk_uuid': event_data.get('_uuid', ''),
                'submission_time': submission_time
            }
        )

        # Process participant counts
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


def process_participant(participant_data: dict) -> Tuple[bool, str]:
    """Process a single participant and save to database"""
    try:
        # Handle ISO format datetime with timezone
        submission_time = timezone.make_aware(
            datetime.strptime(participant_data['_submission_time'], '%Y-%m-%dT%H:%M:%S')
        )

        # Get or create partner
        partner_name = participant_data.get('partner', 'Default Partner')
        partner, _ = Partner.objects.get_or_create(
            name=partner_name,
            defaults={'country': 'NG', 'is_active': True}
        )

        participant, created = Participant.objects.update_or_create(
            odk_id=str(participant_data['_id']),
            defaults={
                'partner': partner,
                'first_name': participant_data.get('first_name', ''),
                'surname': participant_data.get('surname', ''),
                'gender': participant_data.get('gender', '').lower(),
                'phone_number': participant_data.get('phone_number', ''),
                'own_phone': participant_data.get('own_phone', False),
                'has_whatsapp': participant_data.get('has_whatsapp', False),
                'email': participant_data.get('email', ''),
                'submission_time': submission_time
            }
        )
        return True, None
    except Exception as e:
        return False, str(e)
        

def process_extension_agent(agent_data: dict) -> Tuple[bool, str]:
    """Process a single extension agent and save to database"""
    try:
        # First process the base participant data
        success, error = process_participant(agent_data)
        if not success:
            return False, error
        
        participant = Participant.objects.get(odk_id=str(agent_data['_id']))
        agent, created = ExtensionAgent.objects.update_or_create(
            participant=participant,
            defaults={
                'designation': agent_data.get('designation', ''),
                'education_level': agent_data.get('education_level', 'tertiary'),
                'organization': agent_data.get('organization', ''),
                'organization_type': agent_data.get('organization_type', ''),
                'operational_level': agent_data.get('operational_level', ''),
                'number_of_farmers': int(agent_data.get('number_of_farmers', 0)),
                'states': agent_data.get('states', []),
                'akilimo_tools': agent_data.get('akilimo_tools', []),
                'akilimo_formats': agent_data.get('akilimo_formats', []),
                'akilimo_use_cases': agent_data.get('akilimo_use_cases', []),
                'crops': agent_data.get('crops', []),
                'technologies': agent_data.get('technologies', []),
                'is_akilimo_certified': agent_data.get('is_akilimo_certified', False)
            }
        )
        return True, None
    except Exception as e:
        return False, str(e)

def process_farmer(farmer_data: dict) -> Tuple[bool, str]:
    """Process a single farmer and save to database"""
    try:
        # First process the base participant data
        success, error = process_participant(farmer_data)
        if not success:
            return False, error

        # Get or create location
        location, _ = Location.objects.get_or_create(
            hasc1=farmer_data.get('state', ''),
            hasc2=farmer_data.get('lga', ''),
            city=farmer_data.get('city', ''),
            defaults={
                'hasc1_name': farmer_data.get('state_name', ''),
                'hasc2_name': farmer_data.get('lga_name', '')
            }
        )

        participant = Participant.objects.get(odk_id=str(farmer_data['_id']))
        farmer, created = Farmer.objects.update_or_create(
            participant=participant,
            defaults={
                'farm_area': float(farmer_data.get('farm_area', 0)),
                'area_unit': farmer_data.get('area_unit', 'hectare'),
                'location': location,
                'crops': farmer_data.get('crops', []),
                'other_crops': farmer_data.get('other_crops', ''),
                'consent_given_for': farmer_data.get('consent_given_for', []),
                'registration_source': farmer_data.get('registration_source', ''),
                'registration_date': datetime.strptime(farmer_data.get('registration_date', 
                    farmer_data['_submission_time'][:10]), '%Y-%m-%d').date()
            }
        )
        return True, None
    except Exception as e:
        return False, str(e)


def process_partner(partner_data: dict) -> Tuple[bool, str]:
    """Process a single partner and save to database"""
    try:
        # Create or update partner
        partner, created = Partner.objects.update_or_create(
            odk_id=str(partner_data['_id']),
            defaults={
                'name': partner_data.get('name', ''),
                'country': partner_data.get('country', ''),
                'api_key': partner_data.get('api_key', ''),
                'is_active': partner_data.get('is_active', True),
                'organization_type': partner_data.get('organization_type', ''),
                'contact_person': partner_data.get('contact_person', ''),
                'contact_email': partner_data.get('contact_email', ''),
                'contact_phone': partner_data.get('contact_phone', '')
            }
        )

        # Create or update partner location if provided
        if any(key in partner_data for key in ['state', 'lga', 'city']):
            location, _ = Location.objects.get_or_create(
                hasc1=partner_data.get('state', ''),
                hasc2=partner_data.get('lga', ''),
                city=partner_data.get('city', ''),
                defaults={
                    'hasc1_name': partner_data.get('state_name', ''),
                    'hasc2_name': partner_data.get('lga_name', '')
                }
            )
            partner.location = location
            partner.save()

        return True, None
    except Exception as e:
        return False, str(e)
        

def process_scaling_checklist(checklist_data: dict) -> Tuple[bool, str]:
    """Process a single scaling checklist and save to database"""
    try:

         # Get or create partner
        partner_name = checklist_data.get('partner', 'Default Partner')
        partner, _ = Partner.objects.get_or_create(
            name=partner_name,
            defaults={'country': 'NG', 'is_active': True}
        )

        submission_time = timezone.make_aware(
            datetime.strptime(checklist_data['_submission_time'], '%Y-%m-%dT%H:%M:%S')
        )

        checklist, created = ScalingChecklist.objects.update_or_create(
            odk_id=str(checklist_data['_id']),
            defaults={
                'partner': partner,
                'submission_date': submission_time,
                'main_business': checklist_data.get('main_business', ''),
                'core_business': checklist_data.get('core_business', ''),
                'target_groups': checklist_data.get('target_groups', []),
                'main_target_group': checklist_data.get('main_target_group', ''),
                'knows_akilimo': checklist_data.get('knows_akilimo', False),
                'akilimo_relevant': checklist_data.get('akilimo_relevant', False),
                'use_cases': checklist_data.get('use_cases', []),
                'integration_type': checklist_data.get('integration_type', ''),
                'has_mel_system': checklist_data.get('has_mel_system', False),
                'system_type': checklist_data.get('system_type', ''),
                'collects_data': checklist_data.get('collects_data', False),
                'has_farmer_database': checklist_data.get('has_farmer_database', False),
                'has_agrodealer_database': checklist_data.get('has_agrodealer_database', False),
                'odk_uuid': checklist_data.get('_uuid', '')
            }
        )
        return True, None
    except Exception as e:
        return False, str(e)