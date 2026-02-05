from django.urls import path
from . import views
from . import api_views

# app_name = 'accounts'  # Optional but recommended for namespacing

urlpatterns = [
    # Original template-based views (keep for backwards compatibility)
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('admin-login/', views.admin_login, name='admin_login'),
    path('logout/', views.logout_view, name='logout'),
    path('account/', views.account_view, name='account'),
    path('profile/', views.profile_update, name='profile_update'),
    path('user-dashboard/', views.user_dashboard, name='user_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # Legacy API endpoints (keep for backwards compatibility)
    path('api/admin/roles/', views.admin_roles_api, name='admin_roles_api'),
    path('api/admin/permissions/', views.admin_permissions_api, name='admin_permissions_api'),
    path('api/user/activity/', views.user_activity_api, name='user_activity_api'),

    # New REST API endpoints for React frontend
    # Auth
    path('api/session/', api_views.session_api, name='api_session'),
    path('api/login/', api_views.login_api, name='api_login'),
    path('api/admin-login/', api_views.admin_login_api, name='api_admin_login'),
    path('api/signup/', api_views.signup_api, name='api_signup'),
    path('api/logout/', api_views.logout_api, name='api_logout'),

    # User endpoints
    path('api/user/profile/', api_views.user_profile_api, name='api_user_profile'),
    path('api/user/change-password/', api_views.user_change_password_api, name='api_user_change_password'),
    path('api/user/roles/', api_views.user_roles_api, name='api_user_roles'),
    path('api/user/activity/', api_views.user_activity_api_v2, name='api_user_activity_v2'),

    # Admin endpoints
    path('api/admin/stats/', api_views.admin_stats_api, name='api_admin_stats'),
    path('api/admin/users/', api_views.admin_users_api, name='api_admin_users'),
    path('api/admin/users/<int:user_id>/', api_views.admin_user_detail_api, name='api_admin_user_detail'),
    path('api/admin/roles/', api_views.admin_roles_api_v2, name='api_admin_roles_v2'),
    path('api/admin/permissions/', api_views.admin_permissions_api_v2, name='api_admin_permissions_v2'),
    path('api/admin/bulk-grant/', api_views.admin_bulk_grant_api, name='api_admin_bulk_grant'),
    path('api/admin/promote/', api_views.admin_promote_api, name='api_admin_promote'),
    path('api/admin/remove-admin/', api_views.admin_remove_admin_api, name='api_admin_remove'),
    path('api/admin/sync-roles/', api_views.admin_sync_roles_api, name='api_admin_sync_roles'),
]
