from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
<<<<<<< HEAD
from django.core.paginator import Paginator
=======
>>>>>>> 84788627ce78f3da16ca57cf61180eb67855d59e
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncMonth
from datetime import datetime, timedelta
from .integrations.sync_manager import DataSyncManager
from django.contrib import messages
from .forms import UserRegistrationForm, UserProfileForm
from .models import (UserProfile, AkilimoEvent, Participant, ParticipantGroup, Farmer, ExtensionAgent, 
<<<<<<< HEAD
                    ScalingChecklist, Location, DataSyncLog, DataSyncStatus, Partner, FarmerData, ExtensionAgentData)
=======
                    ScalingChecklist, Location, DataSyncLog, DataSyncStatus, Partner)
>>>>>>> 84788627ce78f3da16ca57cf61180eb67855d59e



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
<<<<<<< HEAD
    success_url = reverse_lazy('dashboard:dashboard')  # Changed to include namespace
=======
    success_url = reverse_lazy('dashboard')
>>>>>>> 84788627ce78f3da16ca57cf61180eb67855d59e

    def form_invalid(self, form):
        messages.error(self.request, 'Invalid email or password.')
        return super().form_invalid(form)

<<<<<<< HEAD
    def form_valid(self, form):
        # Clear any existing messages first
        storage = messages.get_messages(self.request)
        for _ in storage:
            pass  # Clear existing messages
            
        response = super().form_valid(form)
        messages.success(self.request, f'Welcome back, {self.request.user.first_name or self.request.user.email}!')
        return response

    def get_success_url(self):
        if not self.request.user.profile.is_profile_complete:
            return reverse_lazy('dashboard:complete_profile')
        return self.success_url

@login_required
def user_logout(request):
    logout(request)
      # Changed to info level
    return redirect('dashboard:login')  # Changed to use direct URL name without namespace

=======
    def get_success_url(self):
        if not self.request.user.profile.is_profile_complete:
            return reverse_lazy('complete_profile')
        return self.success_url

>>>>>>> 84788627ce78f3da16ca57cf61180eb67855d59e


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


<<<<<<< HEAD
=======
@login_required
def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('dashboard:login')


>>>>>>> 84788627ce78f3da16ca57cf61180eb67855d59e

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

<<<<<<< HEAD
@login_required
def events_list(request):
    try:
        user = request.user
        user_partner = UserProfile.objects.get(user=user).partner
        
        # Get all events first
        all_events = AkilimoEvent.objects.all()
        
        # Filter events by matching letters
        events = []
        participant_stats = {}  # Dictionary to store participant data
        partner_letters = set(''.join(c.lower() for c in user_partner.name if c.isalnum()))
        
        for event in all_events:
            event_letters = set(''.join(c.lower() for c in event.partner if c.isalnum()))
            if partner_letters == event_letters:
                # Store participant data in dictionary
                participant_stats[event.id] = {
                    'total_participants': 0,
                    'male_participants': 0,
                    'female_participants': 0
                }
                
                # Process participant data
                if hasattr(event, 'participantRepeat'):
                    for participant in event.participantRepeat:
                        male_count = int(participant.get('participantDetails/participant_male', 0))
                        female_count = int(participant.get('participantDetails/participant_female', 0))
                        participant_stats[event.id]['male_participants'] += male_count
                        participant_stats[event.id]['female_participants'] += female_count
                    
                participant_stats[event.id]['total_participants'] = (
                    participant_stats[event.id]['male_participants'] + 
                    participant_stats[event.id]['female_participants']
                )
                events.append(event)
        
        # Sort events by date
        events = sorted(events, key=lambda x: x.event_date, reverse=True)
        
        # Calculate statistics
        total_events = len(events)
        total_participants = sum(stats['total_participants'] for stats in participant_stats.values())
        
        # Update context to include participant stats
        context = {
            'events': events,
            'total_events': total_events,
            'event_types': {
                'training': sum(1 for event in events if event.event_type == 'training_event'),
                'sensitization': sum(1 for event in events if event.event_type == 'sensitization_event')
            },
            'format_stats': {
                'paper': sum(1 for event in events if event.format == 'paper'),
                'digital': sum(1 for event in events if event.format == 'digital')
            },
            'total_participants': total_participants,
            'participant_stats': participant_stats  # Add participant stats to context
        }
        
        # Pagination
        paginator = Paginator(events, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context['events'] = page_obj
        
    except (AttributeError, ObjectDoesNotExist) as e:
        print(f"Error: {str(e)}")
        context = {
            'events': [],
            'total_events': 0,
            'event_types': {'training': 0, 'sensitization': 0},
            'format_stats': {'paper': 0, 'digital': 0},
            'total_participants': 0,
            'participant_stats': {}
        }
    
    return render(request, 'dashboard/events.html', context)


def farmers_list(request):
    try:
        user = request.user
        user_partner = UserProfile.objects.get(user=user).partner
        if not user_partner:
            raise ObjectDoesNotExist("No partner found for user")
            
        words = user_partner.name.split()
        partner_name = '_'.join(word.capitalize() if word.lower() != 'and' else 'and' 
                              for word in words)
        
        # Get farmers for current partner
        farmers = FarmerData.objects.filter(partner=partner_name).order_by('firstname', 'lastname')
        
        # Calculate insights with safe defaults
        total_farmers = farmers.count()
        gender_distribution = {
            'male': farmers.filter(gender__iexact='male').count(),
            'female': farmers.filter(gender__iexact='female').count()
        }
        
        # Crop statistics with safe defaults
        crop_stats = {
            'cassava': farmers.filter(cassava=True).count(),
            'yam': farmers.filter(yam=True).count(),
            'maize': farmers.filter(maize=True).count(),
            'rice': farmers.filter(rice=True).count(),
            'sorghum': farmers.filter(sorghum=True).count()
        }
        
        # Phone ownership with safe defaults
        phone_stats = {
            'with_phone': farmers.filter(phone_no__isnull=False).exclude(phone_no='').count(),
            'without_phone': farmers.filter(Q(phone_no__isnull=True) | Q(phone_no='')).count()
        }
        
        # Pagination
        paginator = Paginator(farmers, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'farmers': page_obj or [],  # Provide empty list as fallback
            'total_farmers': total_farmers,
            'gender_distribution': gender_distribution,
            'crop_stats': crop_stats,
            'phone_stats': phone_stats,
        }
        
    except (AttributeError, ObjectDoesNotExist) as e:
        # Log the error for debugging
        print(f"Error in farmers_list view: {str(e)}")
        context = {
            'farmers': [],
            'total_farmers': 0,
            'gender_distribution': {'male': 0, 'female': 0},
            'crop_stats': {'cassava': 0, 'yam': 0, 'maize': 0, 'rice': 0, 'sorghum': 0},
            'phone_stats': {'with_phone': 0, 'without_phone': 0},
        }
    
    return render(request, 'dashboard/farmers.html', context)


@login_required
def extension_agents_list(request):
        
    try:
        user = request.user
        user_partner = UserProfile.objects.get(user=user).partner
        partner_name = user_partner.name
        
        # Get extension agents for current partner
        agents = ExtensionAgentData.objects.filter(org=partner_name)
        
        # Basic statistics
        total_agents = agents.count()
        gender_distribution = {
            'male': agents.filter(gender__iexact='male').count(),
            'female': agents.filter(gender__iexact='female').count()
        }
        
        # Education level distribution
        education_levels = agents.values('education').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Total farmers reached
        total_farmers_reached = sum(
            int(float(agent.no_farmers)) if agent.no_farmers else 0 
            for agent in agents
        )
        
        # Technology adoption
        tech_adoption = {
            'paper': agents.filter(paper='TRUE').count(),
            'app': agents.filter(app='TRUE').count(),
            'viamo': agents.filter(viamo='TRUE').count(),
            'dashboard': agents.filter(dashboard='TRUE').count()
        }
        
        # Expertise areas
        expertise_areas = {
            'fertilizer': agents.filter(fertilizer_supply='TRUE').count(),
            'herbicide': agents.filter(herbicide_supply='TRUE').count(),
            'mechanization': agents.filter(mechanization='TRUE').count(),
            'credit': agents.filter(credit='TRUE').count(),
            'market': agents.filter(market='TRUE').count()
        }

        # Pagination - limit to 10 records per page
        paginator = Paginator(agents, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        
        context = {
            'total_agents': total_agents,
            'gender_distribution': gender_distribution,
            'education_levels': education_levels,
            'total_farmers_reached': total_farmers_reached,
            'tech_adoption': tech_adoption,
            'expertise_areas': expertise_areas,
            'agents': page_obj
        }
        
    except (AttributeError, ObjectDoesNotExist):
        context = {
            'total_agents': 0,
            'gender_distribution': {'male': 0, 'female': 0},
            'education_levels': [],
            'total_farmers_reached': 0,
            'tech_adoption': {'paper': 0, 'app': 0, 'viamo': 0, 'dashboard': 0},
            'expertise_areas': {'fertilizer': 0, 'herbicide': 0, 'mechanization': 0, 'credit': 0, 'market': 0},
            'agents': []
        }
    
=======
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
>>>>>>> 84788627ce78f3da16ca57cf61180eb67855d59e
    return render(request, 'dashboard/extension_agents.html', context)