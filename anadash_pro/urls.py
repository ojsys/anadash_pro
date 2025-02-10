from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken import views as token_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('dashboard.api.urls')),
    path('api-auth/', include('rest_framework.urls')),  # Adds login to browsable API
    path('api/token-auth/', token_views.obtain_auth_token),  # Endpoint to get token
    path('', include('dashboard.urls')),
]
