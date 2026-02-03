from django.urls import path
from . import views

# app_name = 'accounts'  # Optional but recommended for namespacing

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]