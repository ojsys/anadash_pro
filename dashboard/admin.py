# dashboard/admin.py
from django.contrib import admin
from .models import (
    Partner, Location, Event, EventAttachment, Participant,
    ParticipantGroup, Farmer, ExtensionAgent, ScalingChecklist,
    DataSyncLog, DataSyncStatus
)

@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'is_active', 'last_sync')
    list_filter = ('is_active', 'country')
    search_fields = ('name',)
    filter_horizontal = ('users',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('city', 'hasc1', 'hasc2', 'hasc1_name', 'hasc2_name')
    list_filter = ('hasc1', 'hasc2')
    search_fields = ('city', 'hasc1', 'hasc2')

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'partner', 'event_type', 'start_date', 'end_date', 'venue')
    list_filter = ('event_type', 'format', 'partner')
    search_fields = ('title', 'venue')
    date_hierarchy = 'start_date'
    readonly_fields = ('created_at', 'updated_at')

@admin.register(EventAttachment)
class EventAttachmentAdmin(admin.ModelAdmin):
    list_display = ('event', 'file_name', 'file_type', 'created_at')
    list_filter = ('file_type', 'created_at')
    search_fields = ('file_name', 'event__title')

@admin.register(ParticipantGroup)
class ParticipantGroupAdmin(admin.ModelAdmin):
    list_display = ('event', 'participant_type', 'male_count', 'female_count', 'total_count')
    list_filter = ('participant_type',)
    search_fields = ('event__title',)

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'surname', 'gender', 'phone_number', 'partner')
    list_filter = ('gender', 'own_phone', 'has_whatsapp', 'partner')
    search_fields = ('first_name', 'surname', 'phone_number', 'email')

@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ('get_farmer_name', 'farm_area', 'area_unit', 'registration_source')
    list_filter = ('area_unit', 'registration_source')
    search_fields = ('participant__first_name', 'participant__surname')
    date_hierarchy = 'registration_date'

    def get_farmer_name(self, obj):
        return f"{obj.participant.first_name} {obj.participant.surname}"
    get_farmer_name.short_description = 'Farmer Name'

@admin.register(ExtensionAgent)
class ExtensionAgentAdmin(admin.ModelAdmin):
    list_display = ('get_agent_name', 'organization', 'designation', 'education_level', 'is_akilimo_certified')
    list_filter = ('education_level', 'is_akilimo_certified', 'organization_type')
    search_fields = ('participant__first_name', 'participant__surname', 'organization')

    def get_agent_name(self, obj):
        return f"{obj.participant.first_name} {obj.participant.surname}"
    get_agent_name.short_description = 'Agent Name'

@admin.register(ScalingChecklist)
class ScalingChecklistAdmin(admin.ModelAdmin):
    list_display = ('partner', 'main_business', 'knows_akilimo', 'has_mel_system', 'submission_date')
    list_filter = (
        'knows_akilimo', 
        'akilimo_relevant',
        'has_mel_system',
        'has_farmer_database',
        'has_agrodealer_database'
    )
    search_fields = ('partner__name', 'main_business')
    date_hierarchy = 'submission_date'

@admin.register(DataSyncLog)
class DataSyncLogAdmin(admin.ModelAdmin):
    list_display = ('partner', 'sync_type', 'start_time', 'end_time', 'status', 'records_processed')
    list_filter = ('sync_type', 'status', 'partner')
    search_fields = ('partner__name',)
    readonly_fields = ('start_time', 'end_time')
    date_hierarchy = 'start_time'

    def has_add_permission(self, request):
        return False  # Prevent manual creation of sync logs
    


@admin.register(DataSyncStatus)
class DataSyncStatusAdmin(admin.ModelAdmin):
    list_display = ('partner', 'form_type', 'status', 'records_processed', 
                   'records_failed', 'started_at', 'completed_at')
    list_filter = ('status', 'form_type', 'partner')
    search_fields = ('partner__name', 'form_type')
    readonly_fields = ('started_at', 'completed_at')

    def has_add_permission(self, request):
        return False  # Prevent manual creation

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']  # Prevent deletion
        return actions

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_save_and_continue'] = False
        extra_context['show_save'] = False
        return super().change_view(request, object_id, form_url, extra_context)
    



class SyncMonitoringAdmin(admin.ModelAdmin):
    change_list_template = 'admin/sync_monitoring.html'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # Get sync statistics
        extra_context['sync_stats'] = {
            'total_syncs': DataSyncStatus.objects.count(),
            'pending': DataSyncStatus.objects.filter(status='pending').count(),
            'in_progress': DataSyncStatus.objects.filter(status='in_progress').count(),
            'completed': DataSyncStatus.objects.filter(status='completed').count(),
            'failed': DataSyncStatus.objects.filter(status='failed').count(),
        }
        
        # Get latest sync status for each form type
        form_types = DataSyncStatus.objects.values_list('form_type', flat=True).distinct()
        latest_syncs = {}
        for form_type in form_types:
            latest_syncs[form_type] = DataSyncStatus.objects.filter(
                form_type=form_type
            ).order_by('-started_at').first()
        
        extra_context['latest_syncs'] = latest_syncs
        
        return super().changelist_view(request, extra_context)
