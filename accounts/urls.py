"""
Atlas Config - URL Configuration

URL patterns for authentication, dashboard, and admin views.
Supports dual login: User (username) and AtlasAdmin (email).
"""

from django.urls import path
from . import views

urlpatterns = [
    # =========================================================================
    # User Authentication
    # =========================================================================
    path('login/', views.user_login_view, name='user_login'),
    path('signup/', views.user_signup_view, name='user_signup'),
    path('logout/', views.user_logout_view, name='user_logout'),

    # =========================================================================
    # Admin Authentication (Separate)
    # =========================================================================
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('admin-logout/', views.admin_logout_view, name='admin_logout'),

    # =========================================================================
    # Password Reset (Shared)
    # =========================================================================
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/<str:token>/', views.reset_password_view, name='reset_password'),

    # =========================================================================
    # User Dashboard
    # =========================================================================
    path('dashboard/', views.user_dashboard_view, name='user_dashboard'),
    path('dashboard/roles/', views.user_roles_view, name='user_roles'),
    path('dashboard/profile/', views.user_profile_view, name='user_profile'),
    path('dashboard/change-password/', views.user_change_password_view, name='user_change_password'),
    path('dashboard/support/', views.user_support_view, name='user_support'),
    path('dashboard/dismiss-message/<int:message_id>/', views.user_dismiss_message_view, name='user_dismiss_message'),

    # =========================================================================
    # Admin Dashboard
    # =========================================================================
    path('admin/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin/profile/', views.admin_profile_view, name='admin_profile'),
    path('admin/change-password/', views.admin_change_password_view, name='admin_change_password'),

    # Admin - User Management
    path('admin/users/', views.admin_users_view, name='admin_users'),
    path('admin/users/<int:user_id>/', views.admin_user_detail_view, name='admin_user_detail'),

    # Admin - Role Management
    path('admin/roles/', views.admin_roles_view, name='admin_roles'),

    # Admin - Administrator Management (Super Admin only)
    path('admin/admins/', views.admin_admins_view, name='admin_admins'),
    path('admin/admins/create/', views.admin_create_admin_view, name='admin_create_admin'),
    path('admin/admins/change-role/', views.admin_change_admin_role_view, name='admin_change_admin_role'),

    # Admin - Audit Log
    path('admin/audit-log/', views.admin_audit_log_view, name='admin_audit_log'),

    # Admin - Messages
    path('admin/messages/', views.admin_messages_view, name='admin_messages'),
    path('admin/messages/create/', views.admin_message_create_view, name='admin_message_create'),

    # =========================================================================
    # HTMX/AJAX Endpoints
    # =========================================================================
    path('htmx/grant-role/', views.htmx_grant_role_view, name='htmx_grant_role'),
    path('htmx/revoke-role/', views.htmx_revoke_role_view, name='htmx_revoke_role'),
    path('htmx/bulk-grant-roles/', views.htmx_bulk_grant_roles_view, name='htmx_bulk_grant_roles'),
    path('htmx/update-role-description/', views.htmx_update_role_description_view, name='htmx_update_role_description'),
    path('htmx/toggle-user-active/<int:user_id>/', views.htmx_toggle_user_active_view, name='htmx_toggle_user_active'),
    path('htmx/search-users/', views.htmx_search_users_view, name='htmx_search_users'),
    path('htmx/user-roles/<int:user_id>/', views.htmx_user_roles_view, name='htmx_user_roles'),

    # =========================================================================
    # Health Check
    # =========================================================================
    path('health/', views.health_check, name='health_check'),

    # =========================================================================
    # Backwards Compatibility Redirects
    # =========================================================================
    path('', views.login_redirect_view, name='home'),
    path('profile/', views.user_profile_view, name='profile'),  # Alias
    path('change-password/', views.user_change_password_view, name='change_password'),  # Alias
]
