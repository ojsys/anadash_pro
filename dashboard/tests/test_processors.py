from django.test import TestCase
from unittest import main
from django.core.exceptions import ValidationError
from django.utils import timezone
from ..models import Partner, Event, Participant, ExtensionAgent, Farmer, ScalingChecklist
from ..integrations.data_processors import (
    EventProcessor, ParticipantProcessor,
    ExtensionAgentProcessor, FarmerProcessor,
    ScalingChecklistProcessor
)
import datetime

class BaseProcessorTestCase(TestCase):
    def setUp(self):
        self.partner = Partner.objects.create(
            name="Test Partner",
            api_key="test_key",
            country="NG"
        )

class EventProcessorTests(BaseProcessorTestCase):
    def setUp(self):
        super().setUp()
        self.processor = EventProcessor(self.partner)
        self.valid_event_data = {
            '_id': '123',
            '_uuid': 'test-uuid',
            'eventDetails/event': 'training_event',
            'eventLocation/startdate': '2025-01-01',
            'eventLocation/enddate': '2025-01-02',
            'eventLocation/hasc1': 'NG.OY',
            'eventLocation/hasc2': 'NG.OY.IB',
            'eventLocation/city': 'Ibadan',
            'eventLocation/venue': 'Test Venue',
            'contentDetails/title': 'Test Event',
            '_submission_time': '2025-01-01T10:00:00Z'
        }

    def test_valid_event_processing(self):
        """Test processing of valid event data"""
        event = self.processor.process(self.valid_event_data)
        self.assertEqual(event.title, 'Test Event')
        self.assertEqual(event.event_type, 'training_event')
        self.assertEqual(event.location.city, 'Ibadan')

    def test_missing_required_fields(self):
        """Test validation of required fields"""
        invalid_data = self.valid_event_data.copy()
        del invalid_data['eventDetails/event']
        with self.assertRaises(ValidationError):
            self.processor.process(invalid_data)

    def test_invalid_date_format(self):
        """Test validation of date formats"""
        invalid_data = self.valid_event_data.copy()
        invalid_data['eventLocation/startdate'] = 'invalid-date'
        with self.assertRaises(ValidationError):
            self.processor.process(invalid_data)

class ExtensionAgentProcessorTests(BaseProcessorTestCase):
    def setUp(self):
        super().setUp()
        self.processor = ExtensionAgentProcessor(self.partner)
        self.valid_ea_data = {
            '_id': '123',
            '_uuid': 'test-uuid',
            'detailsEA/firstName': 'John',
            'detailsEA/surName': 'Doe',
            'detailsEA/gender': 'male',
            'detailsEA/phoneNr': '1234567890',
            'detailsEA/org': 'Test Org',
            'detailsEA/designation': 'Agent',
            'detailsEA/education': 'tertiary',
            'areaOperation/hasc1': 'NG.OY NG.LA',
            'AKILIMOexpertise/tools': 'dashboard worksheets',
            '_submission_time': '2025-01-01T10:00:00Z'
        }

    def test_valid_ea_processing(self):
        """Test processing of valid EA data"""
        ea = self.processor.process(self.valid_ea_data)
        self.assertEqual(ea.participant.first_name, 'John')
        self.assertEqual(ea.organization, 'Test Org')
        self.assertEqual(len(ea.states), 2)

    def test_invalid_state_codes(self):
        """Test validation of state codes"""
        invalid_data = self.valid_ea_data.copy()
        invalid_data['areaOperation/hasc1'] = 'INVALID XX.YY'
        with self.assertRaises(ValidationError):
            self.processor.process(invalid_data)


class FarmerProcessorTests(BaseProcessorTestCase):
    def setUp(self):
        super().setUp()
        self.processor = FarmerProcessor(self.partner)
        self.valid_farmer_data = {
            '_id': '123',
            '_uuid': 'test-uuid',
            'farmerDetails/firstNamePP': 'Jane',
            'farmerDetails/surNamePP': 'Doe',
            'farmerDetails/genderPP': 'female',
            'farmerDetails/phoneNrPP': '1234567890',
            'farmerDetails/ownPhonePP': 'yes',
            'farmerDetails/whatsAppPP': 'yes',
            'farmerDetails/farmAreaPP': '5.5',
            'farmerDetails/area_unit': 'hectare',
            'farmerDetails/hasc1': 'NG.OY',
            'farmerDetails/hasc2': 'NG.OY.IB',
            'farmerDetails/city': 'Ibadan',
            'farmerDetails/cropsPP': 'maize cassava rice',
            'farmerDetails/consent': 'pictures contact_info location',
            'sourceDetails/source': 'EA',
            'sourceDetails/startdate': '2025-01-01',
            '_submission_time': '2025-01-01T10:00:00Z'
        }

    def test_valid_farmer_processing(self):
        """Test processing of valid farmer data"""
        farmer = self.processor.process(self.valid_farmer_data)
        
        # Test participant data
        self.assertEqual(farmer.participant.first_name, 'Jane')
        self.assertEqual(farmer.participant.surname, 'Doe')
        self.assertEqual(farmer.participant.gender, 'female')
        self.assertEqual(farmer.participant.phone_number, '1234567890')
        self.assertTrue(farmer.participant.own_phone)
        self.assertTrue(farmer.participant.has_whatsapp)
        
        # Test farmer-specific data
        self.assertEqual(farmer.farm_area, 5.5)
        self.assertEqual(farmer.area_unit, 'hectare')
        self.assertEqual(set(farmer.crops), {'maize', 'cassava', 'rice'})
        self.assertEqual(set(farmer.consent_given_for), 
                        {'pictures', 'contact_info', 'location'})
        self.assertEqual(farmer.registration_source, 'EA')

    def test_missing_required_fields(self):
        """Test validation of required fields"""
        invalid_data = self.valid_farmer_data.copy()
        del invalid_data['farmerDetails/farmAreaPP']
        with self.assertRaises(ValidationError):
            self.processor.process(invalid_data)

    def test_invalid_farm_area(self):
        """Test validation of farm area value"""
        invalid_data = self.valid_farmer_data.copy()
        invalid_data['farmerDetails/farmAreaPP'] = 'not-a-number'
        with self.assertRaises(ValidationError):
            self.processor.process(invalid_data)

    def test_optional_fields_handling(self):
        """Test handling of optional fields"""
        minimal_data = {
            '_id': '123',
            '_uuid': 'test-uuid',
            'farmerDetails/firstNamePP': 'Jane',
            'farmerDetails/surNamePP': 'Doe',
            'farmerDetails/genderPP': 'female',
            'farmerDetails/farmAreaPP': '5.5',
            'farmerDetails/area_unit': 'hectare',
            'farmerDetails/hasc1': 'NG.OY',
            'farmerDetails/hasc2': 'NG.OY.IB',
            'farmerDetails/city': 'Ibadan',
            'sourceDetails/source': 'EA',
            'sourceDetails/startdate': '2025-01-01',
            '_submission_time': '2025-01-01T10:00:00Z'
        }
        
        farmer = self.processor.process(minimal_data)
        self.assertIsNotNone(farmer)
        self.assertEqual(farmer.crops, [])
        self.assertEqual(farmer.consent_given_for, [])

    def test_location_creation(self):
        """Test location processing"""
        farmer = self.processor.process(self.valid_farmer_data)
        
        self.assertEqual(farmer.location.hasc1, 'NG.OY')
        self.assertEqual(farmer.location.hasc2, 'NG.OY.IB')
        self.assertEqual(farmer.location.city, 'Ibadan')

class ScalingChecklistProcessorTests(BaseProcessorTestCase):
    def setUp(self):
        super().setUp()
        self.processor = ScalingChecklistProcessor(self.partner)
        self.valid_checklist_data = {
            '_id': '123',
            '_uuid': 'test-uuid',
            'Core_business': 'input',
            'main_business': 'input',
            'target_group': 'Farmers Agrodealers',
            'main_target_group': 'Farmers',
            'knowAKILIMO': 'yes',
            'AKILIMORelevant': 'yes',
            'useCase': 'FR PP_WM IC',
            'Integration/support': 'backstopping',
            'MEL/system': 'Manual',
            'MEL/data_collection': 'yes',
            'MEL/farmers_database': 'yes',
            'MEL/agrodealers_database': 'no',
            '_submission_time': '2025-01-01T10:00:00Z'
        }

    def test_valid_checklist_processing(self):
        """Test processing of valid scaling checklist data"""
        checklist = self.processor.process(self.valid_checklist_data)
        
        self.assertEqual(checklist.core_business, 'input')
        self.assertEqual(checklist.main_business, 'input')
        self.assertEqual(set(checklist.target_groups), {'Farmers', 'Agrodealers'})
        self.assertEqual(checklist.main_target_group, 'Farmers')
        self.assertTrue(checklist.knows_akilimo)
        self.assertTrue(checklist.akilimo_relevant)
        self.assertEqual(set(checklist.use_cases), {'FR', 'PP_WM', 'IC'})
        self.assertEqual(checklist.integration_type, 'backstopping')
        self.assertTrue(checklist.has_mel_system)
        self.assertEqual(checklist.system_type, 'Manual')
        self.assertTrue(checklist.collects_data)
        self.assertTrue(checklist.has_farmer_database)
        self.assertFalse(checklist.has_agrodealer_database)

    def test_missing_required_fields(self):
        """Test validation of required fields"""
        invalid_data = self.valid_checklist_data.copy()
        del invalid_data['Core_business']
        with self.assertRaises(ValidationError):
            self.processor.process(invalid_data)

    def test_optional_fields_handling(self):
        """Test handling of optional fields"""
        minimal_data = {
            '_id': '123',
            '_uuid': 'test-uuid',
            'Core_business': 'input',
            'target_group': 'Farmers',
            'main_target_group': 'Farmers',
            '_submission_time': '2025-01-01T10:00:00Z'
        }
        
        checklist = self.processor.process(minimal_data)
        self.assertIsNotNone(checklist)
        self.assertFalse(checklist.knows_akilimo)
        self.assertFalse(checklist.akilimo_relevant)
        self.assertEqual(checklist.use_cases, [])
        self.assertEqual(checklist.integration_type, '')

    def test_boolean_field_processing(self):
        """Test processing of boolean fields"""
        data = self.valid_checklist_data.copy()
        data['MEL/data_collection'] = 'no'
        data['MEL/farmers_database'] = 'invalid'
        
        checklist = self.processor.process(data)
        self.assertFalse(checklist.collects_data)
        self.assertFalse(checklist.has_farmer_database)

if __name__ == '__main__':
    main()