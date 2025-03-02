from .models import SiteSettings

def site_settings(request):
    try:
        settings = SiteSettings.objects.first()
    except:
        settings = None
    return {'site_settings': settings}


def current_partner(request):
    if request.user.is_authenticated:
        try:
            partner = request.user.partner
            return {
                'current_partner': partner
            }
        except:
            return {'current_partner': None}
    return {'current_partner': None}