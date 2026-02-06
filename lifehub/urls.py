"""
Atlas Config - URL Configuration
"""

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings

def home_redirect(request):
    """Redirect home to login or dashboard."""
    from accounts.views import get_current_user
    user = get_current_user(request)
    if user:
        return redirect('user_dashboard')
    return redirect('user_login')

urlpatterns = [
    # Root redirect
    path('', home_redirect, name='home'),

    # Atlas Config routes
    path('', include('accounts.urls')),

    # Django Admin (kept available on a non-conflicting route)
    path('django-admin/', admin.site.urls),
]

# Custom error handlers
handler404 = 'accounts.views.handler404'
handler500 = 'accounts.views.handler500'
