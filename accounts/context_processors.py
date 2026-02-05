"""
Template context processors for Atlas Config.
"""

from django.conf import settings


def site_settings(request):
    """
    Add site-wide settings to template context.
    """
    return {
        'site_name': 'Atlas Config',
        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        'support_emails': [
            'akwuru.david@ul.ie',
            'akintomide.jeremiah@ul.ie',
            'ehealth@ul.ie',
        ],
        'footer_text': 'ehealthhub4cancer',
        'footer_link': 'https://ehealth4cancer.ie',
        'debug': settings.DEBUG,
    }
