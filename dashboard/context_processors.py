from .models import SiteSettings

def site_settings(request):
    try:
        settings = SiteSettings.objects.first()
    except:
        settings = None
    return {'site_settings': settings}