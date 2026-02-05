"""
Atlas Config - URL Configuration
"""

from django.urls import path
from . import views

urlpatterns = [
    # =========================================================================
    # Authentication
    # =========================================================================
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/<str:token>/', views.reset_password_view, name='reset_password'),

    # =========================================================================
    # Dashboard & Profile
    # =========================================================================
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password_view, name='change_password'),

    # =========================================================================
    # Admin Section
    # =========================================================================
    path('dashboard/admin/users/', views.admin_users_view, name='admin_users'),
    path('dashboard/admin/users/<int:user_id>/', views.admin_user_detail_view, name='admin_user_detail'),
    path('dashboard/admin/admins/', views.admin_admins_view, name='admin_admins'),
    path('dashboard/admin/change-role/', views.admin_change_role_view, name='admin_change_role'),
    path('dashboard/admin/audit-log/', views.admin_audit_log_view, name='admin_audit_log'),

    # =========================================================================
    # Health Check
    # =========================================================================
    path('health/', views.health_check, name='health_check'),
]
