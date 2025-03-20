from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='dashboard/login.html'), name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/complete/', views.complete_profile, name='complete_profile'),
    

    path('trigger-sync/', views.trigger_sync, name='trigger-sync'),
    path('events/', views.events_list, name='events'),
    path('farmers/', views.farmers_list, name='farmers'),
    path('extension-agents/', views.extension_agents_list, name='extension-agents'),

    # Password Reset URLs
    path('password-reset/', 
        auth_views.PasswordResetView.as_view(
            template_name='dashboard/password_reset.html',
            email_template_name='dashboard/password_reset_email.html',
            success_url='/password-reset/done/'  # Remove 'dashboard/' prefix
        ),
        name='password_reset'),
    
    path('password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='dashboard/password_reset_done.html'
        ),
        name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='dashboard/password_reset_confirm.html'
        ),
        name='password_reset_confirm'),
    
    path('password-reset-complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='dashboard/password_reset_complete.html'
        ),
        name='password_reset_complete'),


    
    # Partner specific URLs
    
    path('partners/<int:partner_id>/farmers/', views.partner_farmers, name='partner_farmers'),
    path('partners/<int:partner_id>/participants/', views.partner_participants, name='partner_participants'),
    


]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)