from rest_framework import serializers
from django.db.models import Count, Q
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from ..models import (
    Partner, Event, Participant, ExtensionAgent, 
    Farmer, ScalingChecklist, Location, ParticipantGroup,
    DataSyncLog, EventAttachment
)

class ValidatorMixin:
    """Common validation methods"""
    def validate_phone_number(self, value):
        """Validate phone number format"""
        if value and not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits")
        return value

    def validate_dates(self, start_date, end_date):
        """Validate date ranges"""
        if end_date and start_date and end_date < start_date:
            raise serializers.ValidationError("End date must be after start date")
        return start_date, end_date

class LocationSerializer(serializers.ModelSerializer):
    """Enhanced Location serializer with validation"""
    full_location = serializers.SerializerMethodField()
    
    class Meta:
        model = Location
        fields = [
            'id', 'hasc1', 'hasc1_name', 'hasc2', 'hasc2_name', 
            'city', 'latitude', 'longitude', 'full_location'
        ]
        
    def validate_hasc1(self, value):
        """Validate HASC1 code format"""
        if not value.startswith(('NG.', 'TZ.')):
            raise serializers.ValidationError(
                "HASC1 must start with 'NG.' or 'TZ.'"
            )
        return value

    def get_full_location(self, obj):
        """Get formatted full location string"""
        return f"{obj.city}, {obj.hasc2_name} {obj.hasc1_name}"

class PartnerSerializer(serializers.ModelSerializer):
    """Enhanced Partner serializer with validation"""
    active_days = serializers.SerializerMethodField()
    sync_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Partner
        fields = [
            'id', 'name', 'api_key', 'country', 'last_sync',
            'is_active', 'created_at', 'updated_at', 'active_days',
            'sync_status'
        ]
        read_only_fields = ['last_sync', 'created_at', 'updated_at']
        extra_kwargs = {
            'api_key': {'write_only': True},
            'name': {'min_length': 3}
        }

    def validate_country(self, value):
        """Validate country code"""
        valid_countries = ['NG', 'TZ']
        if value not in valid_countries:
            raise serializers.ValidationError(
                f"Country must be one of: {', '.join(valid_countries)}"
            )
        return value

    def get_active_days(self, obj):
        """Calculate days since partner creation"""
        return (timezone.now() - obj.created_at).days

    def get_sync_status(self, obj):
        """Get current sync status"""
        if not obj.last_sync:
            return "Never synced"
        days_since_sync = (timezone.now() - obj.last_sync).days
        if days_since_sync > 14:
            return f"Sync needed (Last: {days_since_sync} days ago)"
        return "Up to date"

class PartnerDetailSerializer(PartnerSerializer):
    """Detailed Partner serializer with statistics"""
    total_events = serializers.IntegerField(read_only=True)
    total_participants = serializers.IntegerField(read_only=True)
    total_farmers = serializers.IntegerField(read_only=True)
    total_extension_agents = serializers.IntegerField(read_only=True)

    class Meta(PartnerSerializer.Meta):
        fields = PartnerSerializer.Meta.fields + [
            'total_events', 'total_participants', 
            'total_farmers', 'total_extension_agents'
        ]

class ParticipantGroupSerializer(serializers.ModelSerializer):
    """Enhanced ParticipantGroup serializer"""
    total_count = serializers.IntegerField(read_only=True)
    gender_ratio = serializers.SerializerMethodField()
    
    class Meta:
        model = ParticipantGroup
        fields = [
            'participant_type', 'male_count', 'female_count', 
            'total_count', 'gender_ratio'
        ]
        
    def validate(self, data):
        """Validate participant counts"""
        if data.get('male_count', 0) < 0 or data.get('female_count', 0) < 0:
            raise serializers.ValidationError("Participant counts cannot be negative")
        return data

    def get_gender_ratio(self, obj):
        """Calculate gender ratio"""
        total = obj.male_count + obj.female_count
        if total == 0:
            return {"male": 0, "female": 0}
        return {
            "male": round(obj.male_count / total * 100, 2),
            "female": round(obj.female_count / total * 100, 2)
        }


class EventSerializer(ValidatorMixin, serializers.ModelSerializer):
    """Enhanced Event serializer with validation and transformations"""
    location = LocationSerializer()
    partner = PartnerSerializer(read_only=True)
    participant_groups = ParticipantGroupSerializer(many=True, read_only=True)
    duration_days = serializers.SerializerMethodField()
    total_participants = serializers.SerializerMethodField()
    event_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'partner', 'location', 'title', 'title_full',
            'event_type', 'format', 'start_date', 'end_date',
            'venue', 'topics', 'use_case', 'remarks',
            'participant_groups', 'duration_days', 'total_participants',
            'event_status', 'odk_id', 
            'odk_uuid', 'submission_time', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'odk_id', 'odk_uuid', 'submission_time', 
            'created_at', 'updated_at'
        ]


    def create(self, validated_data):
        location_data = validated_data.pop('location')
        location = Location.objects.create(**location_data)
        event = Event.objects.create(location=location, **validated_data)
        return event

    
    def update(self, instance, validated_data):
        location_data = validated_data.pop('location', None)
        if location_data:
            Location.objects.filter(id=instance.location.id).update(**location_data)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
    

    def validate(self, data):
        """Validate event data"""
        # Validate dates
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        self.validate_dates(start_date, end_date)
        
        # Validate venue if event is not digital
        if data.get('format') != 'digital' and not data.get('venue'):
            raise serializers.ValidationError(
                "Venue is required for non-digital events"
            )
            
        return data

    def get_duration_days(self, obj):
        """Calculate event duration in days"""
        if obj.end_date and obj.start_date:
            return (obj.end_date - obj.start_date).days + 1
        return 1

    def get_total_participants(self, obj):
        """Get total participant count"""
        return sum(
            group.total_count 
            for group in obj.participant_groups.all()
        )

    def get_event_status(self, obj):
        """Determine event status based on dates"""
        today = timezone.now().date()
        if obj.end_date < today:
            return "Completed"
        if obj.start_date > today:
            return "Upcoming"
        return "Ongoing"

class ParticipantSerializer(ValidatorMixin, serializers.ModelSerializer):
    """Enhanced Participant serializer"""
    partner = PartnerSerializer(read_only=True)
    event = EventSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    contact_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Participant
        fields = [
            'id', 'partner', 'event', 'first_name', 'surname',
            'full_name', 'gender', 'phone_number', 'own_phone', 
            'has_whatsapp', 'email', 'contact_info', 'odk_id', 
            'submission_time'
        ]
        read_only_fields = ['odk_id', 'submission_time']

    def validate_email(self, value):
        """Custom email validation"""
        if value and Participant.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def validate_phone_number(self, value):
        """Enhanced phone number validation"""
        value = super().validate_phone_number(value)
        if value and Participant.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Phone number already exists")
        return value

    def get_full_name(self, obj):
        """Get formatted full name"""
        return f"{obj.first_name} {obj.surname}".strip()

    def get_contact_info(self, obj):
        """Get formatted contact information"""
        contact = []
        if obj.phone_number:
            contact.append(f"Phone: {obj.phone_number}")
            if obj.has_whatsapp:
                contact.append("(WhatsApp)")
        if obj.email:
            contact.append(f"Email: {obj.email}")
        return " | ".join(contact) if contact else "No contact info"
    


class FarmerSerializer(ValidatorMixin, serializers.ModelSerializer):
    """Enhanced Farmer serializer with validation and transformations"""
    participant = ParticipantSerializer()
    location = LocationSerializer()
    farm_size_hectares = serializers.SerializerMethodField()
    crops_count = serializers.SerializerMethodField()
    registration_age = serializers.SerializerMethodField()
    consent_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Farmer
        fields = [
            'id', 'participant', 'farm_area', 'farm_size_hectares',
            'area_unit', 'location', 'crops', 'crops_count',
            'other_crops', 'consent_given_for', 'consent_details',
            'registration_source', 'registration_date',
            'registration_age'
        ]
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=Farmer.objects.all(),
                fields=['participant', 'registration_date']
            )
        ]

    def validate_farm_area(self, value):
        """Validate farm area"""
        if value <= 0:
            raise serializers.ValidationError("Farm area must be greater than 0")
        if value > 10000:  # Maximum 10,000 hectares/acres
            raise serializers.ValidationError("Farm area seems unrealistically large")
        return value

    def validate_crops(self, value):
        """Validate crops list"""
        valid_crops = {'maize', 'cassava', 'rice', 'yam', 'other'}
        invalid_crops = set(value) - valid_crops
        if invalid_crops:
            raise serializers.ValidationError(
                f"Invalid crops: {', '.join(invalid_crops)}"
            )
        return value

    def get_farm_size_hectares(self, obj):
        """Convert farm size to hectares if needed"""
        if obj.area_unit == 'acre':
            return round(obj.farm_area * 0.404686, 2)
        return obj.farm_area

    def get_crops_count(self, obj):
        """Get number of crops grown"""
        return len(obj.crops)

    def get_registration_age(self, obj):
        """Get days since registration"""
        return (timezone.now().date() - obj.registration_date).days

    def get_consent_details(self, obj):
        """Format consent information"""
        return {
            'pictures': 'pictures' in obj.consent_given_for,
            'contact_info': 'contact_info' in obj.consent_given_for,
            'location': 'location' in obj.consent_given_for
        }

class ExtensionAgentSerializer(ValidatorMixin, serializers.ModelSerializer):
    """Enhanced ExtensionAgent serializer"""
    participant = ParticipantSerializer()
    expertise_level = serializers.SerializerMethodField()
    coverage_stats = serializers.SerializerMethodField()
    tools_summary = serializers.SerializerMethodField()
    activity_metrics = serializers.SerializerMethodField()
    
    class Meta:
        model = ExtensionAgent
        fields = [
            'id', 'participant', 'designation', 'education_level',
            'organization', 'organization_type', 'operational_level',
            'number_of_farmers', 'states', 'akilimo_tools',
            'akilimo_formats', 'akilimo_use_cases', 'crops',
            'technologies', 'is_akilimo_certified', 'expertise_level',
            'coverage_stats', 'tools_summary', 'activity_metrics'
        ]
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=ExtensionAgent.objects.all(),
                fields=['participant', 'organization']
            )
        ]

    def validate(self, data):
        """Validate EA data"""
        # Validate states based on country
        if data['participant']['partner']['country'] == 'NG':
            for state in data['states']:
                if not state.startswith('NG.'):
                    raise serializers.ValidationError(
                        f"Invalid state code for Nigeria: {state}"
                    )
        # Add similar validation for Tanzania
        
        # Validate number of farmers
        if data['number_of_farmers'] > 10000:
            raise serializers.ValidationError(
                "Number of farmers seems unrealistically large"
            )
            
        return data

    def get_expertise_level(self, obj):
        """Calculate expertise level based on multiple factors"""
        score = 0
        # Education
        education_scores = {
            'primary': 1,
            'secondary': 2,
            'tertiary': 3
        }
        score += education_scores.get(obj.education_level, 0)
        
        # Tools and technologies
        score += len(obj.akilimo_tools) * 0.5
        score += len(obj.technologies) * 0.5
        
        # Certification
        if obj.is_akilimo_certified:
            score += 2
            
        # Return level based on score
        if score >= 6:
            return "Expert"
        elif score >= 4:
            return "Advanced"
        elif score >= 2:
            return "Intermediate"
        return "Basic"

    def get_coverage_stats(self, obj):
        """Get coverage statistics"""
        return {
            'states_count': len(obj.states),
            'farmers_per_state': round(obj.number_of_farmers / len(obj.states), 2) if obj.states else 0,
            'states_list': obj.states
        }

    def get_tools_summary(self, obj):
        """Summarize tools and technologies"""
        return {
            'akilimo_tools': len(obj.akilimo_tools),
            'formats': len(obj.akilimo_formats),
            'use_cases': len(obj.akilimo_use_cases),
            'technologies': len(obj.technologies)
        }

    def get_activity_metrics(self, obj):
        """Get activity metrics"""
        events = Event.objects.filter(
            partner=obj.participant.partner,
            enumeratorDetails__phoneNrEN=obj.participant.phone_number
        )
        return {
            'total_events': events.count(),
            'recent_events': events.filter(
                start_date__gte=timezone.now() - timezone.timedelta(days=90)
            ).count(),
            'farmers_reached': obj.number_of_farmers,
            'average_farmers_per_event': round(
                obj.number_of_farmers / events.count()
                if events.count() > 0 else 0, 
                2
            )
        }

class ScalingChecklistSerializer(serializers.ModelSerializer):
    """Enhanced ScalingChecklist serializer"""
    partner = PartnerSerializer(read_only=True)
    readiness_score = serializers.SerializerMethodField()
    integration_details = serializers.SerializerMethodField()
    mel_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = ScalingChecklist
        fields = [
            'id', 'partner', 'submission_date', 'main_business',
            'core_business', 'target_groups', 'main_target_group',
            'knows_akilimo', 'akilimo_relevant', 'use_cases',
            'integration_type', 'has_mel_system', 'system_type',
            'collects_data', 'has_farmer_database',
            'has_agrodealer_database', 'odk_id', 'odk_uuid',
            'readiness_score', 'integration_details', 'mel_summary'
        ]
        read_only_fields = ['odk_id', 'odk_uuid']

    def get_readiness_score(self, obj):
        """Calculate scaling readiness score"""
        score = 0
        
        # Knowledge and relevance
        if obj.knows_akilimo:
            score += 20
        if obj.akilimo_relevant:
            score += 20
            
        # Use cases
        score += len(obj.use_cases) * 5
        
        # MEL system
        if obj.has_mel_system:
            score += 15
        if obj.collects_data:
            score += 10
        if obj.has_farmer_database:
            score += 15
        if obj.has_agrodealer_database:
            score += 10
            
        return min(score, 100)  # Cap at 100

    def get_integration_details(self, obj):
        """Get detailed integration information"""
        return {
            'integration_type': obj.integration_type,
            'use_cases_count': len(obj.use_cases),
            'use_cases_list': obj.use_cases,
            'target_groups': obj.target_groups
        }

    def get_mel_summary(self, obj):
        """Summarize MEL capabilities"""
        return {
            'has_mel_system': obj.has_mel_system,
            'system_type': obj.system_type if obj.has_mel_system else None,
            'data_collection': obj.collects_data,
            'database_status': {
                'farmers': obj.has_farmer_database,
                'agrodealers': obj.has_agrodealer_database
            }
        }

# Filtering Mixins
class FilterMixin:
    """Mixin for common filtering capabilities"""
    @property
    def filterset_fields(self):
        """Define filterable fields"""
        return {
            'Partner': ['country', 'is_active'],
            'Event': ['event_type', 'format', 'start_date', 'end_date'],
            'Participant': ['gender', 'has_whatsapp'],
            'Farmer': ['area_unit', 'registration_source'],
            'ExtensionAgent': ['education_level', 'is_akilimo_certified'],
            'ScalingChecklist': ['has_mel_system', 'system_type']
        }.get(self.Meta.model.__name__, [])



class DataSyncLogSerializer(serializers.ModelSerializer):
    """Serializer for sync logs"""
    partner = PartnerSerializer(read_only=True)

    class Meta:
        model = DataSyncLog
        fields = [
            'id', 'partner', 'sync_type', 'start_time', 'end_time',
            'status', 'records_processed', 'errors'
        ]

class SyncResultSerializer(serializers.Serializer):
    """Serializer for sync operation results"""
    success = serializers.BooleanField()
    timestamp = serializers.DateTimeField()
    results = serializers.DictField()

class SyncStatusSerializer(serializers.Serializer):
    """Serializer for sync status"""
    last_sync = serializers.DateTimeField()
    recent_syncs = DataSyncLogSerializer(many=True)
    sync_stats = serializers.DictField()

class PendingChangesSerializer(serializers.Serializer):
    """Serializer for pending changes"""
    pending_pull = serializers.DictField()
    pending_push = serializers.DictField()
    last_checked = serializers.DateTimeField()