# dashboard/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from typing import Dict
import json

class ListField(models.TextField):
    """Custom field for storing lists in SQLite"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return []
        try:
            return json.loads(value)
        except:
            return []

    def to_python(self, value):
        if isinstance(value, list):
            return value
        if value is None:
            return []
        try:
            return json.loads(value)
        except:
            return []

    def get_prep_value(self, value):
        if value is None:
            return '[]'
        return json.dumps(value)



class Partner(models.Model):
    name = models.CharField(max_length=255)
    country = models.CharField(max_length=2)
    last_sync = models.DateTimeField(null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    users = models.ManyToManyField(User, related_name='partners')

    def __str__(self):
        return self.name

    def to_odk_format(self) -> Dict:
        return {
            'name': self.name,
            'country': self.country,
            'organization_type': self.organization_type,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'is_active': self.is_active,
            'location': self.location.to_odk_format() if self.location else None
        }

class Location(models.Model):
    hasc1 = models.CharField(max_length=10)
    hasc1_name = models.CharField(max_length=255)
    hasc2 = models.CharField(max_length=10)
    hasc2_name = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)

    class Meta:
        unique_together = ('hasc1', 'hasc2', 'city')

    def __str__(self):
        return f"{self.city}, {self.hasc2}"

    def to_odk_format(self) -> Dict:
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'country': self.country,
            'region': self.region,
            'district': self.district
        }

class AkilimoEvent(models.Model):
    EVENT_TYPES = [
        ('sensitization_event', 'Sensitization Event'),
        ('training_event', 'Training Event'),
    ]
    
    FORMAT_CHOICES = [
        ('paper', 'Paper'),
        ('digital', 'Digital'),
    ]

    # ODK Metadata
    odk_id = models.CharField(max_length=50, unique=True)
    odk_uuid = models.CharField(max_length=50, unique=True)
    submission_time = models.DateTimeField()
    submitted_by = models.CharField(max_length=255, null=True)

    # Event Details
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, null=True)
    partner = models.CharField(max_length=255, null=True)

    # Content Details
    title = models.CharField(max_length=255, null=True)
    title_full = models.TextField(null=True, blank=True)
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES)
    topics = models.TextField(null=True)
    use_case = models.CharField(max_length=50, null=True)
    image = models.CharField(max_length=255, blank=True, null=True)

    # Location Details
    city = models.CharField(max_length=255, null=True)
    hasc1 = models.CharField(max_length=10, null=True)
    hasc2 = models.CharField(max_length=10, null=True)
    hasc1_name = models.CharField(max_length=50, null=True)
    hasc2_name = models.CharField(max_length=50, null=True)
    venue = models.CharField(max_length=255, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)

    # Dates
    event_date = models.DateField(null=True)
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)

    # Enumerator Details
    enumerator_first_name = models.CharField(max_length=255, blank=True, null=True)
    enumerator_surname = models.CharField(max_length=255, blank=True, null=True)
    enumerator_gender = models.CharField(max_length=10, blank=True, null=True)
    enumerator_phone = models.CharField(max_length=20, blank=True, null=True)
    enumerator_organization = models.CharField(max_length=255, blank=True, null=True)
    enumerator_designation = models.CharField(max_length=100, blank=True, null=True)

    # Participant Details - Stored as JSON
    participantRepeat = models.JSONField(default=list)
    participantRepeat_count = models.IntegerField(default=0)

    # Services
    complementary_services = models.CharField(max_length=255, blank=True, null=True)
    input_types = models.CharField(max_length=255, blank=True, null=True)
    input_organizations = models.CharField(max_length=255, blank=True, null=True)

    # System fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} - {self.partner} ({self.event_date})"

    @property
    def total_participants(self):
        """Calculate total participants from participantRepeat JSON"""
        total = 0
        for group in self.participantRepeat:
            male_count = int(group.get('participantRepeat/participant_male', 0))
            female_count = int(group.get('participantRepeat/participant_female', 0))
            total += male_count + female_count
        return total

    @property
    def participant_summary(self):
        """Get summary of participants by type"""
        summary = {}
        for group in self.participantRepeat:
            participant_type = group.get('participantRepeat/participantLabel', '')
            male_count = int(group.get('participantRepeat/participant_male', 0))
            female_count = int(group.get('participantRepeat/participant_female', 0))
            summary[participant_type] = {
                'male': male_count,
                'female': female_count,
                'total': male_count + female_count
            }
        return summary

    class Meta:
        ordering = ['-event_date']
        indexes = [
            models.Index(fields=['partner']),
            models.Index(fields=['event_date']),
            models.Index(fields=['hasc1', 'hasc2']),
        ]


class Event(models.Model):
    EVENT_TYPES = [
        ('training_event', 'Training Event'),
        ('sensitization_event', 'Sensitization Event'),
        ('digital_event', 'Digital Event')
    ]
    FORMAT_CHOICES = [
        ('paper', 'Paper'),
        ('digital', 'Digital'),
        ('hybrid', 'Hybrid')
    ]

    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, null=True)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    title_full = models.TextField(null=True, blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    venue = models.CharField(max_length=255)
    topics = models.TextField(blank=True)
    use_case = models.CharField(max_length=50, blank=True)
    remarks = models.TextField(blank=True)
    odk_id = models.CharField(max_length=50, unique=True)
    odk_uuid = models.CharField(max_length=50, unique=True)
    submission_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def to_odk_format(self) -> Dict:
        return {
            'title': self.title,
            'event_type': self.event_type,
            'format': self.format,
            'venue': self.venue,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'topics': self.topics,
            'location': self.location.to_odk_format() if self.location else None
        }


class EventAttachment(models.Model):
    """Files and attachments associated with events"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attachments')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=100)  # MIME type
    odk_file_id = models.CharField(max_length=50)
    download_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event.title} - {self.file_name}"

    class Meta:
        ordering = ['-created_at']


class Participant(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female')
    ]
    
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True)
    first_name = models.CharField(max_length=255)
    surname = models.CharField(max_length=255)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    own_phone = models.BooleanField(default=False)
    has_whatsapp = models.BooleanField(default=False)
    email = models.EmailField(null=True, blank=True)
    odk_id = models.CharField(max_length=50)
    submission_time = models.DateTimeField()

    def __str__(self):
        return f"{self.first_name} {self.surname}"

    def to_odk_format(self) -> Dict:
        return {
            'first_name': self.first_name,
            'surname': self.surname,
            'phone_number': self.phone_number,
            'gender': self.gender,
            'own_phone': self.own_phone,
            'has_whatsapp': self.has_whatsapp,
            'event_id': str(self.event.id) if self.event else None
        }


class ParticipantGroup(models.Model):
    """Track aggregated participant counts by type"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='participant_groups')
    participant_type = models.CharField(max_length=50)  # e.g., 'farmers', 'extension_agents'
    male_count = models.IntegerField(default=0)
    female_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.event.title} - {self.participant_type}"

    @property
    def total_count(self):
        return self.male_count + self.female_count

    class Meta:
        unique_together = ['event', 'participant_type']

class Farmer(models.Model):
    participant = models.OneToOneField(Participant, on_delete=models.CASCADE)
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, null=True)
    farm_area = models.DecimalField(max_digits=10, decimal_places=2)
    area_unit = models.CharField(max_length=20, choices=[
        ('hectare', 'Hectare'),
        ('acre', 'Acre')
    ])
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    crops = ListField(blank=True)
    other_crops = models.TextField(blank=True)
    consent_given_for = ListField(blank=True)
    registration_source = models.CharField(max_length=50)
    registration_date = models.DateField()

    def __str__(self):
        return f"Farmer: {self.participant}"

    def to_odk_format(self) -> Dict:
        return {
            'participant_id': str(self.participant.id),
            'farm_area': self.farm_area,
            'area_unit': self.area_unit,
            'crops': self.crops,
            'registration_date': self.registration_date.isoformat(),
            'registration_source': self.registration_source,
            'location': self.location.to_odk_format() if self.location else None
        }


class FarmerData(models.Model):
    index = models.CharField(max_length=10, null=True)
    partner = models.CharField(max_length=100, null=True)
    firstname = models.CharField(max_length=255, null=True)
    lastname = models.CharField(max_length=255, null=True)
    gender = models.CharField(max_length=10, null=True)
    phone_no = models.CharField(max_length=20, null=True)
    own_phone = models.BooleanField(default=False, null=True)
    crops = models.CharField(max_length=255, null=True)
    crops_other = models.CharField(max_length=255, null=True)
    farm_area = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    area_unit = models.CharField(max_length=20, null=True)
    cassava = models.BooleanField(default=False, null=True)
    yam = models.BooleanField(default=False, null=True)
    maize = models.BooleanField(default=False, null=True)
    rice = models.BooleanField(default=False, null=True)
    sorghum = models.BooleanField(default=False, null=True)
    
    def __str__(self):
        return f"{self.firstname} - {self.lastname}: {self.gender}"

class ExtensionAgent(models.Model):
    participant = models.OneToOneField(Participant, on_delete=models.CASCADE)
    designation = models.CharField(max_length=255)
    education_level = models.CharField(max_length=50, choices=[
        ('primary', 'Primary'),
        ('secondary', 'Secondary'),
        ('tertiary', 'Tertiary')
    ])
    organization = models.CharField(max_length=255)
    organization_type = models.CharField(max_length=50)
    operational_level = models.CharField(max_length=20)
    number_of_farmers = models.IntegerField(default=0)
    states = ListField(blank=True)
    akilimo_tools = ListField(blank=True)
    akilimo_formats = ListField(blank=True)
    akilimo_use_cases = ListField(blank=True)
    crops = ListField(blank=True)
    technologies = ListField(blank=True)
    is_akilimo_certified = models.BooleanField(default=False)

    def __str__(self):
        return f"EA: {self.participant}"

    def to_odk_format(self) -> Dict:
        return {
            'participant_id': str(self.participant.id),
            'organization': self.organization,
            'education_level': self.education_level,
            'is_akilimo_certified': self.is_akilimo_certified,
            'number_of_farmers': self.number_of_farmers
        }


class ExtensionAgentData(models.Model):
    index = models.IntegerField(default=0)
    firstname = models.CharField(max_length=255, blank=True, null=True)
    lastname = models.CharField(max_length=255, blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    phone_no = models.CharField(max_length=20, blank=True, null=True)
    phone_no2 = models.CharField(max_length=20, blank=True, null=True)
    whatsapp = models.CharField(max_length=5, blank=True, null=True)
    whatsapp2 = models.CharField(max_length=5, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    age = models.CharField(max_length=3, blank=True, null=True)
    education = models.CharField(max_length=50, blank=True, null=True)
    designation = models.CharField(max_length=255, blank=True, null=True)
    type_org = models.CharField(max_length=50, blank=True, null=True)
    org = models.CharField(max_length=255, blank=True, null=True)
    org_other = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    area_level = models.CharField(max_length=10, blank=True, null=True)
    hasc1 = models.CharField(max_length=255, blank=True, null=True)
    hasc2 = models.CharField(max_length=255, blank=True, null=True)
    no_farmers = models.CharField(max_length=10, blank=True, null=True)
    date_added = models.CharField(max_length=20, blank=True, null=True)
    certified = models.CharField(max_length=5, blank=True, null=True)
    use_case = models.CharField(max_length=255, blank=True, null=True)
    format = models.CharField(max_length=255, blank=True, null=True)
    tools = models.CharField(max_length=255, blank=True, null=True)
    otherAKILIMOexpertise = models.CharField(max_length=255, blank=True, null=True)
    crops = models.CharField(max_length=255, blank=True, null=True)
    crops_other = models.CharField(max_length=255, blank=True, null=True)
    technologies = models.CharField(max_length=255, blank=True, null=True)
    technologies_other = models.CharField(max_length=255, blank=True, null=True)
    equipment = models.CharField(max_length=255, blank=True, null=True)
    equipment_other = models.CharField(max_length=255, blank=True, null=True)
    services = models.CharField(max_length=255, blank=True, null=True)
    input_type = models.CharField(max_length=255, blank=True, null=True)
    credit_types = models.CharField(max_length=255, blank=True, null=True)
    market_type = models.CharField(max_length=255, blank=True, null=True)
    paper = models.CharField(max_length=5, blank=True, null=True)
    app = models.CharField(max_length=5, blank=True, null=True)
    viamo = models.CharField(max_length=5, blank=True, null=True)
    arifu = models.CharField(max_length=5, blank=True, null=True)
    dashboard = models.CharField(max_length=5, blank=True, null=True)
    worksheet = models.CharField(max_length=5, blank=True, null=True)
    instructions = models.CharField(max_length=5, blank=True, null=True)
    farmerfriendly_videos = models.CharField(max_length=5, blank=True, null=True)
    short_videos = models.CharField(max_length=5, blank=True, null=True)
    cartoon_guides = models.CharField(max_length=5, blank=True, null=True)
    postcards = models.CharField(max_length=5, blank=True, null=True)
    RYA_app = models.CharField(max_length=5, blank=True, null=True)
    FR = models.CharField(max_length=5, blank=True, null=True)
    IC = models.CharField(max_length=5, blank=True, null=True)
    WM_PP = models.CharField(max_length=5, blank=True, null=True)
    SP_HS = models.CharField(max_length=5, blank=True, null=True)
    input = models.CharField(max_length=5, blank=True, null=True)
    credit = models.CharField(max_length=5, blank=True, null=True)
    market = models.CharField(max_length=5, blank=True, null=True)
    fertilizer_supply = models.CharField(max_length=5, blank=True, null=True)
    herbicide_supply = models.CharField(max_length=5, blank=True, null=True)
    cuttings_supply = models.CharField(max_length=5, blank=True, null=True)
    mechanization = models.CharField(max_length=5, blank=True, null=True)
    indirect_financial = models.CharField(max_length=5, blank=True, null=True)
    individual_credit = models.CharField(max_length=5, blank=True, null=True)
    group_lending = models.CharField(max_length=5, blank=True, null=True)
    intermediary_credit = models.CharField(max_length=5, blank=True, null=True)
    market_information = models.CharField(max_length=5, blank=True, null=True)
    market_access = models.CharField(max_length=5, blank=True, null=True)
    crop_insurance = models.CharField(max_length=5, blank=True, null=True)

    def __str__(self):
        return f"{self.firstname} {self.lastname}"

    class Meta:
        verbose_name = "Extension Agent Data"
        verbose_name_plural = "Extension Agent Data"


class ScalingChecklist(models.Model):
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE)
    submission_date = models.DateTimeField()
    main_business = models.CharField(max_length=50)
    core_business = models.CharField(max_length=50)
    target_groups = ListField(blank=True)
    main_target_group = models.CharField(max_length=50)
    knows_akilimo = models.BooleanField(default=False)
    akilimo_relevant = models.BooleanField(default=False)
    use_cases = ListField(blank=True)
    integration_type = models.CharField(max_length=50)
    has_mel_system = models.BooleanField(default=False)
    system_type = models.CharField(max_length=50, blank=True)
    collects_data = models.BooleanField(default=False)
    has_farmer_database = models.BooleanField(default=False)
    has_agrodealer_database = models.BooleanField(default=False)
    odk_id = models.CharField(max_length=50, unique=True)
    odk_uuid = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"Checklist: {self.partner.name} ({self.submission_date})"

    def to_odk_format(self) -> Dict:
        return {
            'main_business': self.main_business,
            'core_business': self.core_business,
            'has_mel_system': self.has_mel_system,
            'system_type': self.system_type,
            'submission_date': self.submission_date.isoformat()
        }

class DataSyncLog(models.Model):
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE)
    sync_type = models.CharField(max_length=50)  # 'pull' or 'push'
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True)
    status = models.CharField(max_length=20)  # 'success', 'failed', 'partial'
    records_processed = models.IntegerField(default=0)
    errors = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.partner} - {self.sync_type} - {self.start_time}"


class DataSyncStatus(models.Model):
    SYNC_STATUS = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ]
    
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE)
    form_type = models.CharField(max_length=50)  # e.g., 'events', 'participants'
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=SYNC_STATUS)
    records_processed = models.IntegerField(default=0)
    records_failed = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.partner.name} - {self.form_type} - {self.status}"


###### User Profile Update ###########

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    partner = models.ForeignKey(Partner, on_delete=models.SET_NULL, null=True)
    phone_number = models.CharField(max_length=20, blank=True)
    position = models.CharField(max_length=100, blank=True)
    is_profile_complete = models.BooleanField(default=False)
    is_profile_locked = models.BooleanField(default=False)  # New field
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.partner.name if self.partner else 'No Partner'}"


class SiteSettings(models.Model):
    logo = models.ImageField(upload_to='site/', help_text="Site logo")
    favicon = models.ImageField(upload_to='site/', help_text="Site favicon")
    site_name = models.CharField(max_length=100, default="AKILIMO")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        return "Site Settings"

    def save(self, *args, **kwargs):
        if SiteSettings.objects.exists() and not self.pk:
            raise ValidationError('Only one site settings instance is allowed')
        return super().save(*args, **kwargs)