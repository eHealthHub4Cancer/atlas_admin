# views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import AtlasSignUpForm, PasswordChangeForm, AdminUserPermissionsForm, BulkGrantPermissionsForm
from .models import AtlasUser, Permission
from django.db import connection, DatabaseError


WEBAPI_SCHEMA = "bioc_webapi3_schema_v3"


def get_webapi_permissions():
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT id, name
            FROM {WEBAPI_SCHEMA}.sec_role
            ORDER BY name;
            """
        )
        return cursor.fetchall()


def get_webapi_roles():
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT id, name
            FROM {WEBAPI_SCHEMA}.sec_role
            ORDER BY name;
            """
        )
        return cursor.fetchall()


def get_webapi_role_id(role_name):
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT id
            FROM {WEBAPI_SCHEMA}.sec_role
            WHERE LOWER(name) = LOWER(%s)
            LIMIT 1;
            """,
            [role_name],
        )
        result = cursor.fetchone()
        return result[0] if result else None


def ensure_webapi_user(user):
    login = user.username.lower()
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT id
            FROM {WEBAPI_SCHEMA}.sec_user
            WHERE login = %s;
            """,
            [login],
        )
        result = cursor.fetchone()
        if result:
            return result[0]

        cursor.execute(
            f"""
            INSERT INTO {WEBAPI_SCHEMA}.sec_user (id, login, name)
            VALUES (nextval('{WEBAPI_SCHEMA}.sec_user_sequence'), %s, %s)
            RETURNING id;
            """,
            [login, user.username],
        )
        return cursor.fetchone()[0]


def sync_permissions_from_webapi():
    try:
        webapi_permissions = get_webapi_permissions()
    except DatabaseError:
        return Permission.objects.order_by('name')

    for external_id, name in webapi_permissions:
        Permission.objects.update_or_create(
            name=name,
            defaults={'external_id': external_id},
        )
    return Permission.objects.order_by('name')


def sync_user_permissions_to_webapi(user, permissions):
    if not permissions:
        return
    webapi_user_id = ensure_webapi_user(user)
    permission_ids = [permission.external_id for permission in permissions if permission.external_id]
    if not permission_ids:
        return
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            DELETE FROM {WEBAPI_SCHEMA}.sec_user_role
            WHERE user_id = %s;
            """,
            [webapi_user_id],
        )
        for permission_id in permission_ids:
            cursor.execute(
                f"""
                INSERT INTO {WEBAPI_SCHEMA}.sec_user_role (id, user_id, role_id)
                VALUES (nextval('{WEBAPI_SCHEMA}.sec_user_role_sequence'), %s, %s)
                ON CONFLICT DO NOTHING;
                """,
                [webapi_user_id, permission_id],
            )


def sync_user_role_to_webapi(user):
    role_id = get_webapi_role_id(user.role)
    if not role_id:
        return
    webapi_user_id = ensure_webapi_user(user)
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            DELETE FROM {WEBAPI_SCHEMA}.sec_user_role
            WHERE user_id = %s;
            """,
            [webapi_user_id],
        )
        cursor.execute(
            f"""
            INSERT INTO {WEBAPI_SCHEMA}.sec_user_role (id, user_id, role_id)
            VALUES (nextval('{WEBAPI_SCHEMA}.sec_user_role_sequence'), %s, %s)
            ON CONFLICT DO NOTHING;
            """,
            [webapi_user_id, role_id],
        )


def get_current_user(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    try:
        return AtlasUser.objects.get(id=user_id)
    except AtlasUser.DoesNotExist:
        return None


def signup(request):
    if request.method == 'POST':
        form = AtlasSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # if the user is a superuser, please dump into sec_user and sec_user_role tables
            role_id = 2 if getattr(user, 'is_superuser', False) else 2

            try:
                ensure_webapi_user(user)
                sync_user_role_to_webapi(user)
            except DatabaseError:
                messages.warning(request, 'Account created, but WebAPI sync was unavailable.')

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
            if user.is_disabled:
                messages.error(request, 'Your account has been disabled. Please contact an admin.')
                return render(request, 'accounts/login.html')
            if user.check_password(password):
                # Store user info in session
                request.session['user_id'] = user.id
                request.session['username'] = user.username
                request.session['role'] = user.role
                messages.success(request, f'Welcome back, {username}!')
                return redirect('account')
            else:
                messages.error(request, 'Invalid username or password.')
        except AtlasUser.DoesNotExist:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'accounts/login.html')

def logout_view(request):
    request.session.flush()
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


def account_view(request):
    user = get_current_user(request)
    if not user:
        messages.error(request, 'Please log in to view your account.')
        return redirect('login')

    if request.method == 'POST':
        form = PasswordChangeForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your password has been updated.')
            return redirect('account')
    else:
        form = PasswordChangeForm(user)

    permissions = user.permissions.order_by('name')
    return render(
        request,
        'accounts/account.html',
        {
            'user_profile': user,
            'permissions': permissions,
            'form': form,
        },
    )


def admin_dashboard(request):
    user = get_current_user(request)
    if not user:
        messages.error(request, 'Please log in to access the admin dashboard.')
        return redirect('login')

    permissions = sync_permissions_from_webapi()
    users = AtlasUser.objects.prefetch_related('permissions').order_by('username')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_user':
            form = AdminUserPermissionsForm(request.POST, permissions_queryset=permissions)
            if form.is_valid():
                target_user = AtlasUser.objects.get(id=form.cleaned_data['user_id'])
                target_user.is_disabled = form.cleaned_data['is_disabled']
                target_user.save()
                selected_permissions = form.cleaned_data['permissions']
                target_user.permissions.set(selected_permissions)
                try:
                    sync_user_permissions_to_webapi(target_user, selected_permissions)
                except DatabaseError:
                    messages.warning(request, 'Saved locally, but WebAPI permission sync failed.')
                messages.success(request, f'Updated {target_user.username}.')
                return redirect('admin_dashboard')
        elif action == 'bulk_grant':
            form = BulkGrantPermissionsForm(
                request.POST,
                users_queryset=users,
                permissions_queryset=permissions,
            )
            if form.is_valid():
                selected_users = form.cleaned_data['user_ids']
                selected_permissions = form.cleaned_data['permissions']
                for target_user in selected_users:
                    target_user.permissions.add(*selected_permissions)
                    try:
                        sync_user_permissions_to_webapi(target_user, target_user.permissions.all())
                    except DatabaseError:
                        messages.warning(request, f'Local update for {target_user.username} saved, but WebAPI sync failed.')
                messages.success(request, 'Granted permissions to selected users.')
                return redirect('admin_dashboard')

    bulk_form = BulkGrantPermissionsForm(users_queryset=users, permissions_queryset=permissions)
    user_forms = []
    for target_user in users:
        initial_permissions = target_user.permissions.all()
        user_forms.append(
            {
                'user': target_user,
                'form': AdminUserPermissionsForm(
                    initial={
                        'user_id': target_user.id,
                        'is_disabled': target_user.is_disabled,
                        'permissions': initial_permissions,
                    },
                    permissions_queryset=permissions,
                ),
            }
        )

    return render(
        request,
        'accounts/admin_dashboard.html',
        {
            'user_profile': user,
            'permissions': permissions,
            'bulk_form': bulk_form,
            'user_forms': user_forms,
        },
    )
