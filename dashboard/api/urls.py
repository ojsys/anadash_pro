from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from rest_framework.authtoken import views as token_views

router = DefaultRouter()
router.register(r'partners', views.PartnerViewSet, basename='partner')
router.register(r'events', views.EventViewSet, basename='event')
router.register(r'participants', views.ParticipantViewSet, basename='participant')
router.register(r'farmers', views.FarmerViewSet, basename='farmer')
router.register(r'extension-agents', views.ExtensionAgentViewSet, basename='extension-agent')
router.register(r'scaling-checklists', views.ScalingChecklistViewSet, basename='scaling-checklist')

router.register(r'sync', views.SyncViewSet, basename='sync')

urlpatterns = [
    path('', views.api_root, name='api-root'),
    path('', include(router.urls)),
    path('token/', token_views.obtain_auth_token, name='obtain-token'),
]