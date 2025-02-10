from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Count, Q
from .serializers import (
    PartnerSerializer, PartnerDetailSerializer,
    EventSerializer, ParticipantSerializer,
    FarmerSerializer, ExtensionAgentSerializer,
    ScalingChecklistSerializer, LocationSerializer,
    DataSyncLogSerializer, SyncResultSerializer,
    SyncStatusSerializer, PendingChangesSerializer
)
from ..models import (
    Partner, Event, Participant, ExtensionAgent,
    Farmer, ScalingChecklist, Location, DataSyncLog
)
from ..integrations.sync_manager import DataSyncManager
import logging




logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request, format=None):
    """
    API root view showing available endpoints
    """
    if request.user.is_authenticated:
        return Response({
            'partners': reverse('partner-list', request=request, format=format),
            'events': reverse('event-list', request=request, format=format),
            'participants': reverse('participant-list', request=request, format=format),
            'farmers': reverse('farmer-list', request=request, format=format),
            'extension-agents': reverse('extension-agent-list', request=request, format=format),
            'scaling-checklists': reverse('scaling-checklist-list', request=request, format=format),
            #'sync': reverse('sync-list', request=request, format=format),
        })
    else:
        return Response({
            'message': 'Welcome to the AKILIMO API. Please authenticate to access the endpoints.',
            'auth_endpoints': {
                'login': reverse('rest_framework:login', request=request, format=format),
                'token': reverse('obtain-token', request=request, format=format),
            }
        })



class BaseViewSet(viewsets.ModelViewSet):
    """Base ViewSet with common functionality"""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    def get_partner(self):
        """Get partner associated with user"""
        return self.request.user.partners.first()

    def perform_create(self, serializer):
        """Ensure partner is set on create"""
        serializer.save(partner=self.get_partner())

class PartnerViewSet(viewsets.ModelViewSet):
    """ViewSet for Partner model"""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'country']
    ordering_fields = ['name', 'created_at', 'last_sync']
    filterset_fields = ['country', 'is_active']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PartnerDetailSerializer
        return PartnerSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return Partner.objects.all()
        # Using the new partners relationship
        return self.request.user.partners.all()

    def perform_create(self, serializer):
        """Ensure new partner is associated with creating user"""
        partner = serializer.save()
        partner.users.add(self.request.user)

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get detailed partner statistics"""
        partner = self.get_object()
        
        try:
            stats = {
                'events_count': Event.objects.filter(partner=partner).count(),
                'participants_count': Participant.objects.filter(partner=partner).count(),
                'farmers_count': Farmer.objects.filter(participant__partner=partner).count(),
                'extension_agents_count': ExtensionAgent.objects.filter(
                    participant__partner=partner
                ).count(),
                'sync_status': {
                    'last_sync': partner.last_sync,
                    'successful_syncs': DataSyncLog.objects.filter(
                        partner=partner,
                        status='success'
                    ).count(),
                    'failed_syncs': DataSyncLog.objects.filter(
                        partner=partner,
                        status='failed'
                    ).count(),
                }
            }
            
            # Add additional statistics
            if partner.last_sync:
                stats['sync_status']['days_since_last_sync'] = (
                    timezone.now() - partner.last_sync
                ).days
            
            # Add event type distribution
            event_types = Event.objects.filter(partner=partner).values(
                'event_type'
            ).annotate(count=Count('id'))
            stats['event_type_distribution'] = {
                item['event_type']: item['count'] for item in event_types
            }
            
            return Response(stats)
            
        except Exception as e:
            return Response(
                {'error': f'Error fetching statistics: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def add_user(self, request, pk=None):
        """Add a user to partner"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Not authorized'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        partner = self.get_object()
        user_id = request.data.get('user_id')
        
        try:
            user = User.objects.get(id=user_id)
            partner.users.add(user)
            return Response({'status': 'User added successfully'})
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def remove_user(self, request, pk=None):
        """Remove a user from partner"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Not authorized'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        partner = self.get_object()
        user_id = request.data.get('user_id')
        
        try:
            user = User.objects.get(id=user_id)
            if partner.users.count() <= 1:
                return Response(
                    {'error': 'Cannot remove last user from partner'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            partner.users.remove(user)
            return Response({'status': 'User removed successfully'})
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class EventViewSet(BaseViewSet):
    """ViewSet for Event model"""
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['title', 'venue', 'topics']
    ordering_fields = ['start_date', 'created_at']
    filterset_fields = {
        'event_type': ['exact'],
        'format': ['exact'],
        'start_date': ['gte', 'lte'],
        'end_date': ['gte', 'lte']
    }

    def get_queryset(self):
        user_partners = self.request.user.partners.all()
        return Event.objects.filter(
            partner__in=user_partners
        ).select_related('location', 'partner')

    @action(detail=True, methods=['get'])
    def participants_summary(self, request, pk=None):
        """Get participant summary for event"""
        event = self.get_object()
        summary = {
            'total_participants': event.participant_groups.aggregate(
                total=Count('id')
            )['total'],
            'gender_distribution': event.participant_groups.aggregate(
                male=Count('male_count'),
                female=Count('female_count')
            ),
            'by_type': event.participant_groups.values(
                'participant_type'
            ).annotate(count=Count('id'))
        }
        return Response(summary)

class ParticipantViewSet(BaseViewSet):
    """ViewSet for Participant model"""
    serializer_class = ParticipantSerializer
    search_fields = ['first_name', 'surname', 'phone_number']
    ordering_fields = ['submission_time']
    filterset_fields = ['gender', 'own_phone', 'has_whatsapp']

    def get_queryset(self):
        return Participant.objects.filter(
            partner=self.get_partner()
        ).select_related('event')

class FarmerViewSet(BaseViewSet):
    """ViewSet for Farmer model"""
    serializer_class = FarmerSerializer
    search_fields = [
        'participant__first_name', 
        'participant__surname',
        'participant__phone_number'
    ]
    ordering_fields = ['registration_date', 'farm_area']
    filterset_fields = {
        'area_unit': ['exact'],
        'registration_source': ['exact'],
        'registration_date': ['gte', 'lte'],
        'farm_area': ['gte', 'lte']
    }

    def get_queryset(self):
        return Farmer.objects.filter(
            participant__partner=self.get_partner()
        ).select_related('participant', 'location')

    @action(detail=False, methods=['get'])
    def crops_distribution(self, request):
        """Get crop distribution statistics"""
        farmers = self.get_queryset()
        crops_stats = {}
        for farmer in farmers:
            for crop in farmer.crops:
                crops_stats[crop] = crops_stats.get(crop, 0) + 1
        return Response(crops_stats)

class ExtensionAgentViewSet(BaseViewSet):
    """ViewSet for ExtensionAgent model"""
    serializer_class = ExtensionAgentSerializer
    search_fields = [
        'participant__first_name',
        'participant__surname',
        'organization'
    ]
    ordering_fields = ['number_of_farmers']
    filterset_fields = ['education_level', 'is_akilimo_certified']

    def get_queryset(self):
        return ExtensionAgent.objects.filter(
            participant__partner=self.get_partner()
        ).select_related('participant')

class ScalingChecklistViewSet(BaseViewSet):
    """ViewSet for ScalingChecklist model"""
    serializer_class = ScalingChecklistSerializer
    search_fields = ['main_business', 'core_business']
    ordering_fields = ['submission_date']
    filterset_fields = ['has_mel_system', 'system_type']

    def get_queryset(self):
        return ScalingChecklist.objects.filter(
            partner=self.get_partner()
        )

class SyncViewSet(viewsets.ViewSet):
    """ViewSet for sync operations"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def trigger_sync(self, request):
        """Trigger manual sync operation"""
        try:
            partner = self.request.user.partner_set.first()
            if not partner:
                return Response(
                    {"error": "No partner associated with user"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            direction = request.data.get('direction', 'pull')
            sync_manager = DataSyncManager(partner)

            if direction == 'pull':
                results = sync_manager.sync_from_odk()
            else:
                form_type = request.data.get('form_type')
                form_id = sync_manager.api_client.FORM_IDS.get(form_type)
                if not form_id:
                    return Response(
                        {"error": "Invalid form type"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                results = sync_manager.sync_to_odk(
                    form_id, 
                    request.data.get('data', [])
                )

            serializer = SyncResultSerializer(data={
                "success": True,
                "results": results,
                "timestamp": timezone.now()
            })
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Sync API error: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def sync_status(self, request):
        """Get sync status and history"""
        try:
            partner = self.request.user.partner_set.first()
            if not partner:
                return Response(
                    {"error": "No partner associated with user"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            recent_logs = DataSyncLog.objects.filter(
                partner=partner
            ).order_by('-start_time')[:10]

            serializer = SyncStatusSerializer(data={
                "last_sync": partner.last_sync,
                "recent_syncs": recent_logs,
                "sync_stats": {
                    "total_success": DataSyncLog.objects.filter(
                        partner=partner, 
                        status='success'
                    ).count(),
                    "total_failed": DataSyncLog.objects.filter(
                        partner=partner, 
                        status='failed'
                    ).count()
                }
            })
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Sync status API error: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )