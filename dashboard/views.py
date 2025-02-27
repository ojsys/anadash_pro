from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .integrations.sync_manager import DataSyncManager
from django.contrib import messages
from .forms import UserRegistrationForm, UserProfileForm
from .models import UserProfile



@login_required
def trigger_sync(request):
    partner = request.user.partners.first()
    if not partner:
        return JsonResponse({'error': 'No partner found'}, status=400)
    
    try:
        sync_manager = DataSyncManager(partner)
        # Only pull data from ODK
        sync_results = sync_manager.sync_from_odk()
        
        return JsonResponse({
            'status': 'success',
            'results': {
                'partners': sync_results['partners'],
                'events': sync_results['events'],
                'participants': sync_results['participants'],
                'extension_agents': sync_results['extension_agents'],
                'farmers': sync_results['farmers'],
                'checklists': sync_results['checklists'],
                'errors': sync_results['errors']
            }
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)


class CustomLoginView(LoginView):
    template_name = 'dashboard/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('dashboard')

    def form_invalid(self, form):
        messages.error(self.request, 'Invalid email or password.')
        return super().form_invalid(form)

    def get_success_url(self):
        if not self.request.user.profile.is_profile_complete:
            return reverse_lazy('complete_profile')
        return self.success_url



########## Register
def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            login(request, user)
            messages.success(request, 'Registration successful. Please complete your profile.')
            return redirect('dashboard:complete_profile')
    else:
        form = UserRegistrationForm()
    return render(request, 'dashboard/register.html', {'form': form})

############User Profile
@login_required
def complete_profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.is_profile_complete = True
            profile.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('dashboard:dashboard')
    else:
        form = UserProfileForm(instance=profile)
    return render(request, 'dashboard/complete_profile.html', {'form': form})


@login_required
def profile_view(request):
    user = request.user
    profile = user.profile
    
    if request.method == 'POST':
        if profile.is_profile_locked:
            messages.error(request, 'Your profile is locked. Please contact an administrator to make changes.')
            return redirect('dashboard:profile')
            
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.is_profile_locked = True  # Lock the profile after update
            profile.save()
            messages.success(request, 'Profile updated successfully. Profile is now locked for future changes.')
            return redirect('dashboard:profile')
    else:
        form = UserProfileForm(instance=profile)
    
    context = {
        'form': form,
        'user': user,
        'profile': profile
    }
    return render(request, 'dashboard/profile.html', context)


@login_required
def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('dashboard:login')



@login_required
def dashboard_home(request):
    partner = request.user.partners.first()
    context = {
        'partner': partner,
        'last_sync': partner.last_sync if partner else None
    }
    return render(request, 'dashboard/home.html', context)



@login_required
def events_list(request):
    return render(request, 'dashboard/events.html')

@login_required
def farmers_list(request):
    return render(request, 'dashboard/farmers.html')

@login_required
def extension_agents_list(request):
    return render(request, 'dashboard/extension_agents.html')