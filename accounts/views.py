# views.py
import logging
from urllib.parse import urlencode

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.db import connections, DatabaseError, transaction
from django.core.paginator import Paginator
from django.db.models import Q

from .forms import (
    AtlasSignUpForm,
    PasswordChangeForm,
    AdminUserPermissionsForm,
    BulkGrantPermissionsForm,
    AdminLoginForm,
    ProfileUpdateForm,
)
from .models import AtlasUser, Permission, AdminUser


logger = logging.getLogger(__name__)

WEBAPI_SCHEMA = "bioc_webapi3_schema_v3"

# If your Django app uses a DIFFERENT DB than WebAPI tables, define a second DB in settings.py
# and set WEBAPI_DB_ALIAS = "webapi". Otherwise keep "default".
WEBAPI_DB_ALIAS = "default"

PUBLIC_ROLE_NAME = "public"


# ──────────────────────────────────────────────────────────────────────────────
# DB helpers
# ──────────────────────────────────────────────────────────────────────────────

def webapi_connection():
    return connections[WEBAPI_DB_ALIAS]


def fetchone_value(cursor, sql, params=None):
    cursor.execute(sql, params or [])
    row = cursor.fetchone()
    return row[0] if row else None


# ──────────────────────────────────────────────────────────────────────────────
# WebAPI Security Helpers (NO ON CONFLICT TARGETS REQUIRED)
#
# IMPORTANT: Your DB currently does NOT have a UNIQUE constraint on sec_role.name,
# so using "ON CONFLICT (name)" fails.
#
# This implementation avoids ON CONFLICT(...) entirely by doing:
#   SELECT -> if missing then INSERT -> if race then SELECT again.
#
# This is the safest approach WITHOUT changing DB schema.
# If you later add UNIQUE constraints, you can switch to ON CONFLICT targets.
# ──────────────────────────────────────────────────────────────────────────────

def get_webapi_role_id(role_name: str):
    with webapi_connection().cursor() as cursor:
        return fetchone_value(
            cursor,
            f"""
            SELECT id
            FROM {WEBAPI_SCHEMA}.sec_role
            WHERE LOWER(name) = LOWER(%s)
            ORDER BY id
            LIMIT 1;
            """,
            [role_name],
        )


def ensure_webapi_role(cursor, role_name: str) -> int:
    """
    Ensure a role exists and return its id.

    No ON CONFLICT targets, so it works even if sec_role.name isn't unique.
    """
    role_name = (role_name or "").strip()
    if not role_name:
        raise ValueError("role_name cannot be blank")

    # 1) Try find existing
    role_id = fetchone_value(
        cursor,
        f"""
        SELECT id
        FROM {WEBAPI_SCHEMA}.sec_role
        WHERE LOWER(name) = LOWER(%s)
        ORDER BY id
        LIMIT 1;
        """,
        [role_name],
    )
    if role_id is not None:
        return role_id

    # 2) Insert new
    cursor.execute(
        f"""
        INSERT INTO {WEBAPI_SCHEMA}.sec_role (id, name)
        VALUES (nextval('{WEBAPI_SCHEMA}.sec_role_sequence'), %s)
        RETURNING id;
        """,
        [role_name],
    )
    role_id = cursor.fetchone()[0]
    return role_id


def get_webapi_user_id_by_login(cursor, login: str):
    return fetchone_value(
        cursor,
        f"""
        SELECT id
        FROM {WEBAPI_SCHEMA}.sec_user
        WHERE LOWER(login) = LOWER(%s)
        ORDER BY id
        LIMIT 1;
        """,
        [login],
    )


def ensure_webapi_user(cursor, user) -> int:
    """
    Ensure sec_user exists and base roles are assigned:
      - public
      - personal role (name == login)

    Returns sec_user.id.
    """
    login = (user.username or "").strip().lower()
    display_name = (user.username or "").strip()

    if not login:
        raise ValueError("username cannot be blank")

    # 1) Ensure sec_user row
    webapi_user_id = get_webapi_user_id_by_login(cursor, login)
    if webapi_user_id is None:
        cursor.execute(
            f"""
            INSERT INTO {WEBAPI_SCHEMA}.sec_user (id, login, name)
            VALUES (nextval('{WEBAPI_SCHEMA}.sec_user_sequence'), %s, %s)
            RETURNING id;
            """,
            [login, display_name],
        )
        webapi_user_id = cursor.fetchone()[0]

    # 2) Ensure base roles exist
    public_role_id = ensure_webapi_role(cursor, PUBLIC_ROLE_NAME)
    personal_role_id = ensure_webapi_role(cursor, login)

    # 3) Ensure sec_user_role links exist (NO ON CONFLICT)
    ensure_user_role_link(cursor, webapi_user_id, public_role_id)
    ensure_user_role_link(cursor, webapi_user_id, personal_role_id)

    return webapi_user_id


def ensure_user_role_link(cursor, user_id: int, role_id: int):
    """
    Ensure link exists in sec_user_role, without ON CONFLICT targets.

    Handles schema variants with/without "origin" column.
    """
    # First check existence
    exists = fetchone_value(
        cursor,
        f"""
        SELECT 1
        FROM {WEBAPI_SCHEMA}.sec_user_role
        WHERE user_id = %s AND role_id = %s
        LIMIT 1;
        """,
        [user_id, role_id],
    )
    if exists:
        return

    # Try insert with origin, fallback without origin
    try:
        cursor.execute(
            f"""
            INSERT INTO {WEBAPI_SCHEMA}.sec_user_role (id, user_id, role_id, origin)
            VALUES (nextval('{WEBAPI_SCHEMA}.sec_user_role_sequence'), %s, %s, 'SYSTEM');
            """,
            [user_id, role_id],
        )
    except Exception:
        cursor.execute(
            f"""
            INSERT INTO {WEBAPI_SCHEMA}.sec_user_role (id, user_id, role_id)
            VALUES (nextval('{WEBAPI_SCHEMA}.sec_user_role_sequence'), %s, %s);
            """,
            [user_id, role_id],
        )


def set_webapi_user_roles_preserving_base(cursor, user, role_names):
    """
    Replace user's NON-base roles with provided roles,
    preserving:
      - public
      - personal (login)
    """
    login = (user.username or "").strip().lower()
    if not login:
        raise ValueError("username cannot be blank")

    webapi_user_id = ensure_webapi_user(cursor, user)

    # Resolve base roles
    public_role_id = ensure_webapi_role(cursor, PUBLIC_ROLE_NAME)
    personal_role_id = ensure_webapi_role(cursor, login)

    # Resolve desired role ids
    desired_ids = set()
    for rn in (role_names or []):
        rn = (rn or "").strip()
        if rn:
            desired_ids.add(ensure_webapi_role(cursor, rn))

    # Do not manage base roles here
    desired_ids.discard(public_role_id)
    desired_ids.discard(personal_role_id)

    # Delete only non-base role links
    cursor.execute(
        f"""
        DELETE FROM {WEBAPI_SCHEMA}.sec_user_role
        WHERE user_id = %s
          AND role_id NOT IN (%s, %s);
        """,
        [webapi_user_id, public_role_id, personal_role_id],
    )

    # Insert desired roles (ensure link)
    for rid in desired_ids:
        ensure_user_role_link(cursor, webapi_user_id, rid)


# ──────────────────────────────────────────────────────────────────────────────
# "Permissions" Sync (your original design uses sec_role as permissions)
# ──────────────────────────────────────────────────────────────────────────────

def get_webapi_permissions():
    with webapi_connection().cursor() as cursor:
        cursor.execute(
            f"""
            SELECT id, name
            FROM {WEBAPI_SCHEMA}.sec_role
            ORDER BY name;
            """
        )
        return cursor.fetchall()


def sync_permissions_from_webapi():
    try:
        webapi_permissions = get_webapi_permissions()
    except DatabaseError:
        return Permission.objects.order_by("name")

    for external_id, name in webapi_permissions:
        Permission.objects.update_or_create(
            name=name,
            defaults={"external_id": external_id},
        )
    return Permission.objects.order_by("name")


def sync_user_permissions_to_webapi(cursor, user, permissions):
    if not permissions:
        return
    # You are treating Permission.name as a WebAPI role name
    role_names = [p.name for p in permissions if getattr(p, "name", None)]
    set_webapi_user_roles_preserving_base(cursor, user, role_names)


def sync_user_role_to_webapi(cursor, user):
    role_name = getattr(user, "role", None)
    if not role_name:
        return
    set_webapi_user_roles_preserving_base(cursor, user, [role_name])


# ──────────────────────────────────────────────────────────────────────────────
# Local app session helper
# ──────────────────────────────────────────────────────────────────────────────

def get_current_user(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    try:
        return AtlasUser.objects.get(id=user_id)
    except AtlasUser.DoesNotExist:
        return None


def get_current_admin(request):
    admin_user_id = request.session.get("admin_user_id")
    if not admin_user_id:
        return None
    try:
        return AdminUser.objects.get(id=admin_user_id)
    except AdminUser.DoesNotExist:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Views
# ──────────────────────────────────────────────────────────────────────────────

def signup(request):
    if request.method == "POST":
        form = AtlasSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()

            try:
                # Atomic transaction in WebAPI DB
                with transaction.atomic(using=WEBAPI_DB_ALIAS):
                    with webapi_connection().cursor() as cursor:
                        ensure_webapi_user(cursor, user)
                        sync_user_role_to_webapi(cursor, user)
            except Exception as e:
                logger.exception("WebAPI sync failed during signup")
                messages.warning(
                    request,
                    f"Account created, but WebAPI sync failed: {type(e).__name__}: {e}"
                )

            messages.success(request, f"Account created for {user.username}!")
            return redirect("login")
    else:
        form = AtlasSignUpForm()

    return render(request, "accounts/signup.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        try:
            user = AtlasUser.objects.get(username=username)
            if user.is_disabled:
                messages.error(request, "Your account has been disabled. Please contact an admin.")
                return render(request, "accounts/login.html")

            if user.check_password(password):
                request.session["user_id"] = user.id
                request.session["username"] = user.username
                request.session["role"] = user.role
                messages.success(request, "Signed in successfully.")
                return redirect("user_dashboard")

            messages.error(request, "Invalid username or password.")
        except AtlasUser.DoesNotExist:
            messages.error(request, "Invalid username or password.")

    return render(request, "accounts/login.html")


def admin_login(request):
    if request.method == "POST":
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower()
            password = form.cleaned_data["password"]
            try:
                admin_user = AdminUser.objects.get(email__iexact=email)
            except AdminUser.DoesNotExist:
                admin_user = None

            if not admin_user or not admin_user.check_password(password):
                messages.error(request, "Invalid admin email or password.")
            elif not (admin_user.is_admin or admin_user.is_super_admin):
                messages.error(request, "You are not authorized for admin access.")
            else:
                request.session["admin_user_id"] = admin_user.id
                request.session["admin_email"] = admin_user.email
                request.session["is_super_admin"] = admin_user.is_super_admin
                messages.success(request, "Welcome back to the admin console.")
                return redirect("admin_dashboard")
    else:
        form = AdminLoginForm()

    return render(request, "accounts/admin_login.html", {"form": form})


def logout_view(request):
    request.session.flush()
    messages.success(request, "You have been logged out successfully.")
    return redirect("login")


def account_view(request):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Please log in to view your account.")
        return redirect("login")

    permissions = user.permissions.order_by("name")
    profile = getattr(user, "profile", None)
    missing_profile_fields = []
    if not profile:
        missing_profile_fields = ["display name", "email", "affiliation", "prefix"]
    else:
        if not profile.display_name:
            missing_profile_fields.append("display name")
        if not profile.email:
            missing_profile_fields.append("email")
        if not profile.affiliation:
            missing_profile_fields.append("affiliation")
        if not profile.prefix:
            missing_profile_fields.append("prefix")
    profile_completion = 100
    if missing_profile_fields:
        profile_completion = int(((4 - len(missing_profile_fields)) / 4) * 100)
    return render(
        request,
        "accounts/account.html",
        {
            "user_profile": user,
            "profile": profile,
            "permissions": permissions,
            "missing_profile_fields": missing_profile_fields,
            "profile_completion": profile_completion,
        },
    )


def profile_update(request):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Please log in to update your profile.")
        return redirect("login")

    profile = getattr(user, "profile", None)

    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, instance=profile)
        if form.is_valid():
            updated_profile = form.save(commit=False)
            updated_profile.user = user
            updated_profile.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("account")
    else:
        form = ProfileUpdateForm(
            instance=profile,
            initial={
                "display_name": user.username if not profile else profile.display_name,
                "email": "" if not profile else profile.email,
                "affiliation": "" if not profile else profile.affiliation,
                "prefix": "" if not profile else profile.prefix,
            },
        )

    return render(request, "accounts/profile_update.html", {"form": form, "user_profile": user, "profile": profile})


def user_dashboard(request):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Please log in to view your dashboard.")
        return redirect("login")

    if request.method == "POST":
        form = PasswordChangeForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your password has been updated.")
            return redirect("user_dashboard")
    else:
        form = PasswordChangeForm(user)

    permissions = user.permissions.order_by("name")
    profile = getattr(user, "profile", None)
    missing_profile_fields = []
    if not profile:
        missing_profile_fields = ["display name", "email", "affiliation", "prefix"]
    else:
        if not profile.display_name:
            missing_profile_fields.append("display name")
        if not profile.email:
            missing_profile_fields.append("email")
        if not profile.affiliation:
            missing_profile_fields.append("affiliation")
        if not profile.prefix:
            missing_profile_fields.append("prefix")
    needs_profile_update = bool(missing_profile_fields)
    profile_completion = 100
    if missing_profile_fields:
        profile_completion = int(((4 - len(missing_profile_fields)) / 4) * 100)
    return render(
        request,
        "accounts/user_dashboard.html",
        {
            "user": user,
            "user_profile": user,
            "profile": profile,
            "permissions": permissions,
            "form": form,
            "activity_logs": [],
            "needs_profile_update": needs_profile_update,
            "missing_profile_fields": missing_profile_fields,
            "profile_completion": profile_completion,
        },
    )


def _parse_positive_int(value, default=1, max_value=100):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(parsed, max_value))


def _paginate_queryset(queryset, page, page_size):
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    return page_obj, paginator.count


def admin_roles_api(request):
    admin_user = get_current_admin(request)
    if not admin_user:
        return JsonResponse({"detail": "Unauthorized"}, status=401)

    sync_permissions_from_webapi()
    search = (request.GET.get("search") or "").strip()
    filter_value = (request.GET.get("filter") or "all").strip()
    ordering = (request.GET.get("ordering") or "name").strip()
    page = _parse_positive_int(request.GET.get("page"), default=1)
    page_size = _parse_positive_int(request.GET.get("page_size"), default=10, max_value=50)

    queryset = Permission.objects.all()
    if search:
        queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
    if filter_value == "with_id":
        queryset = queryset.filter(external_id__isnull=False)
    elif filter_value == "no_id":
        queryset = queryset.filter(external_id__isnull=True)

    allowed_ordering = {"name", "-name", "external_id", "-external_id"}
    if ordering not in allowed_ordering:
        ordering = "name"
    queryset = queryset.order_by(ordering)

    page_obj, count = _paginate_queryset(queryset, page, page_size)
    results = [
        {
            "name": role.name,
            "external_id": role.external_id,
            "description": role.description,
        }
        for role in page_obj
    ]

    return JsonResponse(
        {
            "results": results,
            "count": count,
            "page": page_obj.number,
            "page_size": page_size,
        }
    )


def admin_permissions_api(request):
    admin_user = get_current_admin(request)
    if not admin_user:
        return JsonResponse({"detail": "Unauthorized"}, status=401)

    sync_permissions_from_webapi()
    search = (request.GET.get("search") or "").strip()
    filter_value = (request.GET.get("filter") or "all").strip()
    ordering = (request.GET.get("ordering") or "name").strip()
    page = _parse_positive_int(request.GET.get("page"), default=1)
    page_size = _parse_positive_int(request.GET.get("page_size"), default=10, max_value=50)

    queryset = Permission.objects.all()
    if search:
        queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
    if filter_value == "with_id":
        queryset = queryset.filter(external_id__isnull=False)
    elif filter_value == "no_id":
        queryset = queryset.filter(external_id__isnull=True)

    allowed_ordering = {"name", "-name", "external_id", "-external_id"}
    if ordering not in allowed_ordering:
        ordering = "name"
    queryset = queryset.order_by(ordering)

    page_obj, count = _paginate_queryset(queryset, page, page_size)
    results = [
        {
            "name": permission.name,
            "external_id": permission.external_id,
            "description": permission.description,
        }
        for permission in page_obj
    ]

    return JsonResponse(
        {
            "results": results,
            "count": count,
            "page": page_obj.number,
            "page_size": page_size,
        }
    )


def user_activity_api(request):
    user = get_current_user(request)
    if not user:
        return JsonResponse({"detail": "Unauthorized"}, status=401)

    profile = getattr(user, "profile", None)
    entries = [
        {
            "summary": "Account created",
            "status": "Success",
            "created_at": user.created_at,
        },
        {
            "summary": "Account updated",
            "status": "Info",
            "created_at": user.updated_at,
        },
    ]
    if profile:
        entries.extend(
            [
                {
                    "summary": "Profile created",
                    "status": "Success",
                    "created_at": profile.created_at,
                },
                {
                    "summary": "Profile updated",
                    "status": "Info",
                    "created_at": profile.updated_at,
                },
            ]
        )

    search = (request.GET.get("search") or "").strip().lower()
    status_filter = (request.GET.get("status") or "all").strip().lower()
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    ordering = (request.GET.get("ordering") or "-created_at").strip()
    page = _parse_positive_int(request.GET.get("page"), default=1)
    page_size = _parse_positive_int(request.GET.get("page_size"), default=8, max_value=50)

    if search:
        entries = [entry for entry in entries if search in entry["summary"].lower()]
    if status_filter != "all":
        entries = [entry for entry in entries if entry["status"].lower() == status_filter]
    if start_date:
        entries = [entry for entry in entries if str(entry["created_at"].date()) >= start_date]
    if end_date:
        entries = [entry for entry in entries if str(entry["created_at"].date()) <= end_date]

    reverse = ordering.startswith("-")
    entries.sort(key=lambda entry: entry["created_at"], reverse=reverse)

    paginator = Paginator(entries, page_size)
    page_obj = paginator.get_page(page)

    results = [
        {
            "summary": entry["summary"],
            "status": entry["status"],
            "created_at": entry["created_at"].isoformat(),
        }
        for entry in page_obj
    ]

    return JsonResponse(
        {
            "results": results,
            "count": paginator.count,
            "page": page_obj.number,
            "page_size": page_size,
        }
    )


def admin_dashboard(request):
    admin_user = get_current_admin(request)
    if not admin_user:
        messages.error(request, "Please log in to access the admin dashboard.")
        return redirect("admin_login")

    is_super_admin = admin_user.is_super_admin

    permissions = sync_permissions_from_webapi()
    permissions_total = permissions.count()
    atlas_users = AtlasUser.objects.select_related("profile").prefetch_related("permissions").order_by("username")
    admin_users = AdminUser.objects.order_by("name")
    all_admin_users = admin_users
    users = atlas_users
    all_atlas_users = atlas_users

    user_search = (request.GET.get("user_search") or "").strip()
    user_filter = (request.GET.get("user_filter") or "all").strip()
    role_search = (request.GET.get("role_search") or "").strip()
    role_filter = (request.GET.get("role_filter") or "all").strip()
    permission_search = (request.GET.get("permission_search") or "").strip()
    permission_filter = (request.GET.get("permission_filter") or "all").strip()

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update_user":
            form = AdminUserPermissionsForm(request.POST, permissions_queryset=permissions)
            if form.is_valid():
                target_user = AtlasUser.objects.get(id=form.cleaned_data["user_id"])
                target_user.is_disabled = form.cleaned_data["is_disabled"]
                target_user.save()

                selected_permissions = form.cleaned_data["permissions"]
                target_user.permissions.set(selected_permissions)

                try:
                    with transaction.atomic(using=WEBAPI_DB_ALIAS):
                        with webapi_connection().cursor() as cursor:
                            sync_user_permissions_to_webapi(cursor, target_user, selected_permissions)
                except Exception as e:
                    logger.exception("WebAPI permission sync failed")
                    messages.warning(
                        request,
                        f"Saved locally, but WebAPI permission sync failed: {type(e).__name__}: {e}"
                    )

                messages.success(request, f"Updated {target_user.username}.")
                return redirect("admin_dashboard")

        elif action == "bulk_grant":
            form = BulkGrantPermissionsForm(
                request.POST,
                users_queryset=users,
                permissions_queryset=permissions,
            )
            if form.is_valid():
                selected_users = form.cleaned_data["user_ids"]
                selected_permissions = form.cleaned_data["permissions"]

                for target_user in selected_users:
                    target_user.permissions.add(*selected_permissions)
                    try:
                        with transaction.atomic(using=WEBAPI_DB_ALIAS):
                            with webapi_connection().cursor() as cursor:
                                sync_user_permissions_to_webapi(cursor, target_user, target_user.permissions.all())
                    except Exception as e:
                        logger.exception("WebAPI permission sync failed (bulk)")
                        messages.warning(
                            request,
                            f"Local update for {target_user.username} saved, but WebAPI sync failed: {type(e).__name__}: {e}"
                        )

                messages.success(request, "Granted permissions to selected users.")
                return redirect("admin_dashboard")

        elif action == "promote_admin" and is_super_admin:
            atlas_user_id = request.POST.get("atlas_user_id")
            make_super_admin = bool(request.POST.get("make_super_admin"))
            if atlas_user_id:
                target_user = AtlasUser.objects.filter(id=atlas_user_id).select_related("profile").first()
                if not target_user:
                    messages.error(request, "Selected user not found.")
                else:
                    profile = getattr(target_user, "profile", None)
                    if not profile or not profile.email:
                        messages.error(request, "Selected user must have a profile email before promotion.")
                    else:
                        admin_user, created = AdminUser.objects.get_or_create(
                            email=profile.email,
                            defaults={
                                "name": profile.display_name or target_user.username,
                                "affiliation": getattr(profile, "affiliation", ""),
                                "is_admin": True,
                                "is_super_admin": make_super_admin,
                                "password": target_user.password,
                            },
                        )
                        if not created:
                            admin_user.is_admin = True
                            if make_super_admin:
                                admin_user.is_super_admin = True
                            admin_user.name = admin_user.name or profile.display_name or target_user.username
                            admin_user.affiliation = admin_user.affiliation or getattr(profile, "affiliation", "")
                            admin_user.save()
                        messages.success(request, f"{target_user.username} can now access admin.")
            return redirect("admin_dashboard")

        elif action == "remove_admin" and is_super_admin:
            admin_email = (request.POST.get("admin_email") or "").strip()
            if admin_email:
                target_admin = AdminUser.objects.filter(email=admin_email).first()
                if target_admin:
                    target_admin.is_admin = False
                    target_admin.is_super_admin = False
                    target_admin.save()
                    messages.success(request, f"Removed admin access for {target_admin.email}.")
            return redirect("admin_dashboard")

    if user_search:
        atlas_users = atlas_users.filter(
            Q(username__icontains=user_search)
            | Q(profile__email__icontains=user_search)
            | Q(profile__affiliation__icontains=user_search)
            | Q(profile__display_name__icontains=user_search)
        )
        admin_users = admin_users.filter(
            Q(name__icontains=user_search)
            | Q(email__icontains=user_search)
            | Q(affiliation__icontains=user_search)
        )

    admin_users_by_email = {admin.email: admin for admin in all_admin_users}
    atlas_email_map = {}
    combined_users = []
    for target_user in atlas_users:
        profile = getattr(target_user, "profile", None)
        profile_email = getattr(profile, "email", None)
        if profile_email:
            atlas_email_map[profile_email] = target_user
        combined_users.append(
            {
                "user": target_user,
                "profile": profile,
                "admin_user": admin_users_by_email.get(profile_email),
                "is_atlas": True,
                "is_admin": profile_email in admin_users_by_email,
            }
        )

    for admin in admin_users:
        if admin.email not in atlas_email_map:
            combined_users.append(
                {
                    "user": None,
                    "profile": None,
                    "admin_user": admin,
                    "is_atlas": False,
                    "is_admin": True,
                }
            )

    if user_filter == "atlas":
        combined_users = [entry for entry in combined_users if entry["is_atlas"]]
    elif user_filter == "admin":
        combined_users = [entry for entry in combined_users if entry["is_admin"]]
    elif user_filter == "active":
        combined_users = [
            entry
            for entry in combined_users
            if entry["is_atlas"] and not entry["user"].is_disabled
        ]
    elif user_filter == "disabled":
        combined_users = [
            entry
            for entry in combined_users
            if entry["is_atlas"] and entry["user"].is_disabled
        ]

    def user_sort_key(entry):
        if entry["is_atlas"]:
            profile = entry["profile"]
            return (getattr(profile, "display_name", "") or entry["user"].username).lower()
        return (entry["admin_user"].name or entry["admin_user"].email).lower()

    combined_users = sorted(combined_users, key=user_sort_key)
    users_paginator = Paginator(combined_users, 10)
    users_page = users_paginator.get_page(request.GET.get("users_page"))

    role_queryset = permissions
    if role_search:
        role_queryset = role_queryset.filter(name__icontains=role_search)
    if role_filter == "with_id":
        role_queryset = role_queryset.filter(external_id__isnull=False)
    elif role_filter == "no_id":
        role_queryset = role_queryset.filter(external_id__isnull=True)
    roles_paginator = Paginator(role_queryset, 10)
    roles_page = roles_paginator.get_page(request.GET.get("roles_page"))

    permission_queryset = permissions
    if permission_search:
        permission_queryset = permission_queryset.filter(name__icontains=permission_search)
    if permission_filter == "with_id":
        permission_queryset = permission_queryset.filter(external_id__isnull=False)
    elif permission_filter == "no_id":
        permission_queryset = permission_queryset.filter(external_id__isnull=True)
    permissions_paginator = Paginator(permission_queryset, 10)
    permissions_page = permissions_paginator.get_page(request.GET.get("permissions_page"))

    bulk_form = BulkGrantPermissionsForm(users_queryset=all_atlas_users, permissions_queryset=permissions)
    user_forms = []
    for entry in users_page:
        target_user = entry.get("user")
        if not target_user:
            user_forms.append({**entry, "form": None})
            continue
        initial_permissions = target_user.permissions.all()
        user_forms.append(
            {
                **entry,
                "form": AdminUserPermissionsForm(
                    initial={
                        "user_id": target_user.id,
                        "is_disabled": target_user.is_disabled,
                        "permissions": initial_permissions,
                    },
                    permissions_queryset=permissions,
                ),
            }
        )

    user_querystring = urlencode(
        {"user_search": user_search, "user_filter": user_filter},
        doseq=True,
    )
    role_querystring = urlencode(
        {"role_search": role_search, "role_filter": role_filter},
        doseq=True,
    )
    permission_querystring = urlencode(
        {"permission_search": permission_search, "permission_filter": permission_filter},
        doseq=True,
    )

    return render(
        request,
        "accounts/admin_dashboard.html",
        {
            "user_profile": admin_user,
            "admin_user": admin_user,
            "is_super_admin": is_super_admin,
            "permissions": permissions_page,
            "roles_page": roles_page,
            "permissions_page": permissions_page,
            "permissions_total": permissions_total,
            "bulk_form": bulk_form,
            "user_forms": user_forms,
            "atlas_users": all_atlas_users,
            "admin_users": all_admin_users,
            "users_page": users_page,
            "user_search": user_search,
            "user_filter": user_filter,
            "role_search": role_search,
            "role_filter": role_filter,
            "permission_search": permission_search,
            "permission_filter": permission_filter,
            "user_querystring": user_querystring,
            "role_querystring": role_querystring,
            "permission_querystring": permission_querystring,
        },
    )
