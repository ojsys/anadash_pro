from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .integrations.sync_manager import DataSyncManager

@login_required
def dashboard_home(request):
    partner = request.user.partners.first()
    context = {
        'partner': partner,
        'last_sync': partner.last_sync if partner else None
    }
    return render(request, 'dashboard/home.html', context)

@login_required
def trigger_sync(request):
    partner = request.user.partners.first()
    if not partner:
        return JsonResponse({'error': 'No partner found'}, status=400)
    
    try:
        sync_manager = DataSyncManager(partner)
        sync_manager.sync_events()
        # Add other sync methods
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def events_list(request):
    return render(request, 'dashboard/events.html')

@login_required
def farmers_list(request):
    return render(request, 'dashboard/farmers.html')

@login_required
def extension_agents_list(request):
    return render(request, 'dashboard/extension_agents.html')