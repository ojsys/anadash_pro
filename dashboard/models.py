# dashboard/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
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
    api_key = models.CharField(max_length=255)
    country = models.CharField(max_length=2)
    last_sync = models.DateTimeField(null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    users = models.ManyToManyField(User, related_name='partners')

    def __str__(self):
        return self.name

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
    submitted_by = models.CharField(max_length=255)

    # Event Details
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    partner = models.CharField(max_length=255)

    # Content Details
    title = models.CharField(max_length=255)
    title_full = models.TextField()
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES)
    topics = models.TextField()
    use_case = models.CharField(max_length=50)
    image = models.CharField(max_length=255, blank=True, null=True)

    # Location Details
    city = models.CharField(max_length=255)
    hasc1 = models.CharField(max_length=10)
    hasc2 = models.CharField(max_length=10)
    hasc1_name = models.CharField(max_length=50)
    hasc2_name = models.CharField(max_length=50)
    venue = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)

    # Dates
    event_date = models.DateField()
    start_date = models.DateField()
    end_date = models.DateField()

    # Enumerator Details
    enumerator_first_name = models.CharField(max_length=255)
    enumerator_surname = models.CharField(max_length=255)
    enumerator_gender = models.CharField(max_length=10)
    enumerator_phone = models.CharField(max_length=20)
    enumerator_organization = models.CharField(max_length=255)
    enumerator_designation = models.CharField(max_length=100)

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

    partner = models.CharField(max_length=100, blank=True, null=True)
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

class DataSyncLog(models.Model):
    """Track data synchronization attempts"""
    partner = models.CharField(max_length=255)  
    sync_type = models.CharField(max_length=20, choices=[
        ('pull', 'Pull from ODK'),
        ('push', 'Push to ODK')
    ])
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True)
    status = models.CharField(max_length=20, choices=[
        ('success', 'Success'),
        ('partial', 'Partial Success'),
        ('failed', 'Failed')
    ])
    records_processed = models.IntegerField(default=0)
    errors = models.TextField(blank=True)

    def __str__(self):
        return f"{self.partner} - {self.sync_type} - {self.start_time}"

    class Meta:
        ordering = ['-start_time']


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