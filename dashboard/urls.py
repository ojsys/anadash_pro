from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('events/', views.events_list, name='events'),
    path('farmers/', views.farmers_list, name='farmers'),
    path('extension-agents/', views.extension_agents_list, name='extension-agents'),
]