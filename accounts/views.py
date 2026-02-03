# views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import AtlasSignUpForm
from .models import AtlasUser
from django.db import connection


def signup(request):
    if request.method == 'POST':
        form = AtlasSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # if the user is a superuser, please dump into sec_user and sec_user_role tables
            role_id = 2 if getattr(user, 'is_superuser', False) else 2

            # with connection.cursor() as cursor:
            #     schema = "bioc_webapi3_schema_v3"

            #     # STEP A: Create the Identity record in sec_user
            #     cursor.execute(f"""
            #         INSERT INTO {schema}.sec_user (id, login, name) 
            #         VALUES (nextval('{schema}.sec_user_sequence'), %s, %s)
            #         ON CONFLICT (login) DO UPDATE SET name = EXCLUDED.name
            #         RETURNING id;
            #     """, [user.username, user.username])
                
            #     atlas_id = cursor.fetchone()[0]

            #     # STEP B: Grant the appropriate role (2 for Admin, 10 for User)
            #     cursor.execute(f"""
            #         INSERT INTO {schema}.sec_user_role (id, user_id, role_id) 
            #         VALUES (nextval('{schema}.sec_user_role_sequence'), %s, %s)
            #         ON CONFLICT DO NOTHING;
            #     """, [atlas_id, role_id])

            messages.success(request, f'Account created for {user.username} with Role ID {role_id}!')
            return redirect('login')
    else:
        form = AtlasSignUpForm()
    
    return render(request, 'accounts/signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            user = AtlasUser.objects.get(username=username)
            if user.check_password(password):
                # Store user info in session
                request.session['user_id'] = user.id
                request.session['username'] = user.username
                messages.success(request, f'Welcome back, {username}!')
                return redirect('home')
            else:
                messages.error(request, 'Invalid username or password.')
        except AtlasUser.DoesNotExist:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'accounts/login.html')

def logout_view(request):
    request.session.flush()
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')