from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncMonth
from datetime import datetime, timedelta
from .integrations.sync_manager import DataSyncManager
from django.contrib import messages
from .forms import UserRegistrationForm, UserProfileForm
from .models import (UserProfile, AkilimoEvent, Participant, ParticipantGroup, Farmer, ExtensionAgent, 
                    ScalingChecklist, Location, DataSyncLog, DataSyncStatus, Partner)



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



def dashboard(request):
    # Event Statistics
    total_events = AkilimoEvent.objects.count()
    events_by_type = AkilimoEvent.objects.values('event_type').annotate(count=Count('id'))
    events_by_month = AkilimoEvent.objects.annotate(
        month=TruncMonth('event_date')
    ).values('month').annotate(count=Count('id')).order_by('month')

    total_orgs = Partner.objects.all().count()

    # Participant Statistics
    total_participants = Participant.objects.count()
    gender_distribution = Participant.objects.values('gender').annotate(count=Count('id'))
    
    # Get farmer data from participants
    farmers = Participant.objects.filter(farmer__isnull=False)
    total_farmers = farmers.count()
    total_farm_area = farmers.aggregate(total=Sum('farmer__farm_area'))['total'] or 0
    
    # Get crops distribution from farmer data
    crops_distribution = {}
    for farmer in farmers:
        for crop in farmer.farmer.crops:
            if crop:  # Check if crop is not empty
                crops_distribution[crop] = crops_distribution.get(crop, 0) + 1

    # Partner Statistics
    partner_events = Participant.objects.values('partner__name').annotate(
        event_count=Count('event', distinct=True)
    ).order_by('-event_count')

    # Extract farmer statistics from participantRepeat
    male_farmers = 0
    female_farmers = 0
    
    for event in AkilimoEvent.objects.all():
        for participant in event.participantRepeat:
            if participant.get('participantDetails/participant') == 'farmers':
                # Convert string values to integers before adding
                male_count = int(participant.get('participantDetails/participant_male', 0))
                female_count = int(participant.get('participantDetails/participant_female', 0))
                
                male_farmers += male_count
                female_farmers += female_count

    total_farmers = male_farmers + female_farmers
    farmer_percentage = (female_farmers / total_farmers * 100) if total_farmers > 0 else 0
    
    # Extract EA statistics from participantRepeat
    male_ea = 0
    female_ea = 0
    
    for event in AkilimoEvent.objects.all():
        for participant in event.participantRepeat:
            if participant.get('participantDetails/participant') == 'NGO_EAs':
                male_count = int(participant.get('participantDetails/participant_male', 0))
                female_count = int(participant.get('participantDetails/participant_female', 0))
                
                male_ea += male_count
                female_ea += female_count

    total_ea = male_ea + female_ea
    ea_percentage = (female_ea / total_ea * 100) if total_ea > 0 else 0


    context = {
        'total_events': total_events,
        'events_by_type': events_by_type,
        'events_by_month': events_by_month,
        'total_participants': total_participants,
        'gender_distribution': gender_distribution,
        'total_farmers': total_farmers,
        'male_farmers': male_farmers,
        'female_farmers': female_farmers,
        'farmer_percentage': farmer_percentage,
        'total_farm_area': total_farm_area,
        'crops_distribution': crops_distribution,
        'partner_events': partner_events,
        'total_ea': total_ea,
        'male_ea': male_ea,
        'female_ea': female_ea,
        'ea_percentage': ea_percentage,
        'total_orgs': total_orgs,
    }
    
    return render(request, 'dashboard/home.html', context)


def partner_farmers(request, partner_id):
    partner = get_object_or_404(Partner, id=partner_id)
    # Add your view logic here
    return render(request, 'dashboard/farmers.html', {'partner': partner})

def partner_participants(request, partner_id):
    partner = get_object_or_404(Partner, id=partner_id)
    # Add your view logic here
    return render(request, 'dashboard/participants.html', {'partner': partner})

def events_list(request):
    # Get events for the current user's partner
    try:
        user = request.user
        partner = UserProfile.objects.get(user=user).partner
        events = AkilimoEvent.objects.filter(partner=partner)
    except (AttributeError, ObjectDoesNotExist):
        events = []
    
    context = {
        'events': events
    }
    return render(request, 'dashboard/events.html', context)

def farmers_list(request):
    # Get farmers for the current user's partner
    try:
        user = request.user
        partner = UserProfile.objects.get(user=user).partner
        farmers = Farmer.objects.filter(partner=partner)
    except (AttributeError, ObjectDoesNotExist):
        farmers = []
    
    context = {
        'farmers': farmers
    }
    return render(request, 'dashboard/farmers.html', context)

@login_required
def extension_agents_list(request):
    partner = request.user.profile.partner
    agents = ExtensionAgent.objects.filter(
        participant__partner=partner
    ).select_related('participant')
    
    context = {
        'agents': agents,
        'partner': partner
    }
    return render(request, 'dashboard/extension_agents.html', context)