"""
SEC Sync Service - Synchronization with WebAPI SEC Tables

This module handles all synchronization between the Atlas Config system
and the external SEC tables (sec_user, sec_role, sec_user_role).

Architecture Overview:
---------------------
The SEC tables are part of the OHDSI WebAPI security schema. This module
provides functions to:

1. Sync roles FROM sec_role to local Role model
2. Ensure users exist in sec_user when created in Atlas
3. Sync role assignments TO sec_user_role when roles are granted/revoked
4. Handle the "base roles" (public, personal) that every user gets

Schema Configuration:
--------------------
The WebAPI schema is configured via DB_SEARCH_PATH in settings.py.
Default schema name is typically like 'bioc_webapi3_schema_v3' or similar.

Important Notes:
- The SEC tables may not have unique constraints, so we avoid ON CONFLICT
- All operations use SELECT-then-INSERT pattern for safety
- Base roles (public, personal) are always preserved
"""

import logging
import os
from django.db import connections, DatabaseError, transaction
from django.conf import settings

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

# WebAPI schema name - can be configured via environment
# Common patterns: bioc_webapi3_schema_v3, bayou_web_api_3_schema_v3, web_security
WEBAPI_SCHEMA = os.environ.get('WEBAPI_SCHEMA', 'web_security')

# Database alias to use for WebAPI tables
# If WebAPI tables are in a different database, configure DATABASES['webapi']
WEBAPI_DB_ALIAS = os.environ.get('WEBAPI_DB_ALIAS', 'default')

# Public role name (every user gets this)
PUBLIC_ROLE_NAME = 'public'

# Whether SEC sync is enabled (can be disabled for testing)
SEC_SYNC_ENABLED = os.environ.get('SEC_SYNC_ENABLED', 'true').lower() == 'true'


# =============================================================================
# Database Helpers
# =============================================================================

def get_webapi_connection():
    """Get the database connection for WebAPI tables."""
    return connections[WEBAPI_DB_ALIAS]


def fetchone_value(cursor, sql, params=None):
    """Execute SQL and return the first column of the first row, or None."""
    cursor.execute(sql, params or [])
    row = cursor.fetchone()
    return row[0] if row else None


def fetchall_tuples(cursor, sql, params=None):
    """Execute SQL and return all rows as list of tuples."""
    cursor.execute(sql, params or [])
    return cursor.fetchall()


# =============================================================================
# SEC Role Operations
# =============================================================================

def get_sec_role_id(cursor, role_name):
    """
    Get the ID of a role from sec_role by name.

    Args:
        cursor: Database cursor
        role_name: Name of the role to find

    Returns:
        int or None: The role ID if found, None otherwise
    """
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


def ensure_sec_role(cursor, role_name):
    """
    Ensure a role exists in sec_role and return its ID.

    This function uses a SELECT-then-INSERT pattern to avoid
    ON CONFLICT issues with schemas that lack unique constraints.

    Args:
        cursor: Database cursor
        role_name: Name of the role to ensure exists

    Returns:
        int: The role ID (existing or newly created)

    Raises:
        ValueError: If role_name is blank
    """
    role_name = (role_name or "").strip()
    if not role_name:
        raise ValueError("role_name cannot be blank")

    # Try to find existing role
    role_id = get_sec_role_id(cursor, role_name)
    if role_id is not None:
        return role_id

    # Insert new role
    cursor.execute(
        f"""
        INSERT INTO {WEBAPI_SCHEMA}.sec_role (id, name)
        VALUES (nextval('{WEBAPI_SCHEMA}.sec_role_sequence'), %s)
        RETURNING id;
        """,
        [role_name],
    )
    return cursor.fetchone()[0]


def get_all_sec_roles(cursor):
    """
    Fetch all roles from sec_role.

    Returns:
        list of tuples: [(id, name), ...]
    """
    return fetchall_tuples(
        cursor,
        f"""
        SELECT id, name
        FROM {WEBAPI_SCHEMA}.sec_role
        ORDER BY name;
        """
    )


# =============================================================================
# SEC User Operations
# =============================================================================

def get_sec_user_id_by_login(cursor, login):
    """
    Get the ID of a user from sec_user by login.

    Args:
        cursor: Database cursor
        login: The login (username) to search for

    Returns:
        int or None: The user ID if found, None otherwise
    """
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


def ensure_sec_user(cursor, user):
    """
    Ensure a user exists in sec_user and has base roles assigned.

    This is the main function called when a new user signs up.
    It creates the sec_user record and assigns:
    - public role (everyone gets this)
    - personal role (named same as login)

    Args:
        cursor: Database cursor
        user: Atlas User model instance

    Returns:
        int: The sec_user.id

    Raises:
        ValueError: If username is blank
    """
    login = (user.username or "").strip().lower()
    display_name = user.display_name or user.username

    if not login:
        raise ValueError("username cannot be blank")

    # Check if user already exists
    sec_user_id = get_sec_user_id_by_login(cursor, login)

    if sec_user_id is None:
        # Create new sec_user
        cursor.execute(
            f"""
            INSERT INTO {WEBAPI_SCHEMA}.sec_user (id, login, name)
            VALUES (nextval('{WEBAPI_SCHEMA}.sec_user_sequence'), %s, %s)
            RETURNING id;
            """,
            [login, display_name],
        )
        sec_user_id = cursor.fetchone()[0]
        logger.info(f"Created sec_user for {login} with id {sec_user_id}")

    # Ensure base roles exist and are assigned
    public_role_id = ensure_sec_role(cursor, PUBLIC_ROLE_NAME)
    personal_role_id = ensure_sec_role(cursor, login)  # Personal role = username

    # Ensure role links exist
    ensure_sec_user_role_link(cursor, sec_user_id, public_role_id)
    ensure_sec_user_role_link(cursor, sec_user_id, personal_role_id)

    return sec_user_id


def update_sec_user(cursor, user):
    """
    Update sec_user record when user profile changes.

    Args:
        cursor: Database cursor
        user: Atlas User model instance
    """
    sec_user_id = _resolve_sec_user_id(cursor, user)

    cursor.execute(
        f"""
        UPDATE {WEBAPI_SCHEMA}.sec_user
        SET name = %s
        WHERE id = %s;
        """,
        [user.display_name, sec_user_id],
    )


# =============================================================================
# SEC User-Role Link Operations
# =============================================================================

def check_sec_user_role_exists(cursor, user_id, role_id):
    """
    Check if a user-role link exists in sec_user_role.

    Args:
        cursor: Database cursor
        user_id: sec_user.id
        role_id: sec_role.id

    Returns:
        bool: True if link exists
    """
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
    return exists is not None


def ensure_sec_user_role_link(cursor, user_id, role_id):
    """
    Ensure a user-role link exists in sec_user_role.

    This function handles schema variants with/without "origin" column.

    Args:
        cursor: Database cursor
        user_id: sec_user.id
        role_id: sec_role.id
    """
    # Check if link already exists
    if check_sec_user_role_exists(cursor, user_id, role_id):
        return

    # Try insert with origin column, fallback without
    try:
        cursor.execute(
            f"""
            INSERT INTO {WEBAPI_SCHEMA}.sec_user_role (id, user_id, role_id, origin)
            VALUES (nextval('{WEBAPI_SCHEMA}.sec_user_role_sequence'), %s, %s, 'ATLAS');
            """,
            [user_id, role_id],
        )
    except Exception:
        # Fallback: schema might not have origin column
        cursor.execute(
            f"""
            INSERT INTO {WEBAPI_SCHEMA}.sec_user_role (id, user_id, role_id)
            VALUES (nextval('{WEBAPI_SCHEMA}.sec_user_role_sequence'), %s, %s);
            """,
            [user_id, role_id],
        )


def remove_sec_user_role_link(cursor, user_id, role_id):
    """
    Remove a user-role link from sec_user_role.

    Args:
        cursor: Database cursor
        user_id: sec_user.id
        role_id: sec_role.id
    """
    cursor.execute(
        f"""
        DELETE FROM {WEBAPI_SCHEMA}.sec_user_role
        WHERE user_id = %s AND role_id = %s;
        """,
        [user_id, role_id],
    )


def get_sec_user_role_ids(cursor, user_id):
    """
    Get all role IDs assigned to a user in sec_user_role.

    Args:
        cursor: Database cursor
        user_id: sec_user.id

    Returns:
        set of int: Role IDs
    """
    rows = fetchall_tuples(
        cursor,
        f"""
        SELECT role_id
        FROM {WEBAPI_SCHEMA}.sec_user_role
        WHERE user_id = %s;
        """,
        [user_id],
    )
    return set(row[0] for row in rows)


# =============================================================================
# High-Level Sync Operations
# =============================================================================

def _resolve_sec_user_id(cursor, user):
    """Resolve sec_user.id for an Atlas user, creating SEC user if needed."""
    user_sec_id = getattr(user, 'sec_user_id', None)
    if user_sec_id:
        return user_sec_id
    return ensure_sec_user(cursor, user)


def sync_roles_from_sec():
    """
    Sync all roles from sec_role to local Role model.

    This function fetches all roles from the SEC database and
    creates/updates corresponding local Role records. It preserves
    any descriptions that have been set locally.

    Returns:
        QuerySet: All local Role objects, ordered by name
    """
    from .models import Role

    if not SEC_SYNC_ENABLED:
        logger.debug("SEC sync disabled, returning local roles only")
        return Role.objects.order_by('name')

    try:
        with get_webapi_connection().cursor() as cursor:
            sec_roles = get_all_sec_roles(cursor)

        for external_id, name in sec_roles:
            Role.objects.update_or_create(
                name=name,
                defaults={}
            )

        logger.info(f"Synced {len(sec_roles)} roles from SEC")

    except DatabaseError as e:
        logger.warning(f"Failed to sync roles from SEC: {e}")

    return Role.objects.order_by('name')


def sync_user_to_sec(user):
    """
    Sync a user to SEC tables (creates sec_user and assigns base roles).

    This should be called after creating a new User.

    Args:
        user: Atlas User model instance

    Returns:
        int or None: The sec_user.id, or None if sync failed/disabled
    """
    if not SEC_SYNC_ENABLED:
        logger.debug(f"SEC sync disabled, skipping sync for {user.username}")
        return None

    try:
        with transaction.atomic(using=WEBAPI_DB_ALIAS):
            with get_webapi_connection().cursor() as cursor:
                sec_user_id = ensure_sec_user(cursor, user)

        logger.info(f"Synced user {user.username} to SEC with id {sec_user_id}")
        return sec_user_id

    except Exception as e:
        logger.exception(f"Failed to sync user {user.username} to SEC: {e}")
        return None


def sync_user_roles_to_sec(user, role_names):
    """
    Sync a user's roles to sec_user_role.

    This replaces all non-base roles with the provided list,
    while preserving the base roles (public, personal).

    Args:
        user: Atlas User model instance
        role_names: List of role names to assign
    """
    if not SEC_SYNC_ENABLED:
        logger.debug(f"SEC sync disabled, skipping role sync for {user.username}")
        return

    try:
        with transaction.atomic(using=WEBAPI_DB_ALIAS):
            with get_webapi_connection().cursor() as cursor:
                login = user.username.lower()
                sec_user_id = _resolve_sec_user_id(cursor, user)

                # Get base role IDs (these are preserved)
                public_role_id = ensure_sec_role(cursor, PUBLIC_ROLE_NAME)
                personal_role_id = ensure_sec_role(cursor, login)
                base_role_ids = {public_role_id, personal_role_id}

                # Get current role IDs
                current_role_ids = get_sec_user_role_ids(cursor, sec_user_id)

                # Build desired role IDs (excluding base roles, they're always kept)
                desired_role_ids = set()
                for role_name in (role_names or []):
                    role_name = (role_name or "").strip()
                    if role_name and role_name.lower() not in (PUBLIC_ROLE_NAME, login):
                        role_id = ensure_sec_role(cursor, role_name)
                        desired_role_ids.add(role_id)

                # Calculate changes (only for non-base roles)
                non_base_current = current_role_ids - base_role_ids
                to_add = desired_role_ids - non_base_current
                to_remove = non_base_current - desired_role_ids

                # Apply changes
                for role_id in to_remove:
                    remove_sec_user_role_link(cursor, sec_user_id, role_id)

                for role_id in to_add:
                    ensure_sec_user_role_link(cursor, sec_user_id, role_id)

        logger.info(f"Synced roles for {user.username}: +{len(to_add)} -{len(to_remove)}")

    except Exception as e:
        logger.exception(f"Failed to sync roles for {user.username} to SEC: {e}")


def grant_role_to_sec(user, role_name):
    """
    Grant a single role to a user in SEC.

    Args:
        user: Atlas User model instance
        role_name: Name of the role to grant

    Returns:
        bool: True if successful
    """
    if not SEC_SYNC_ENABLED:
        return True

    try:
        with transaction.atomic(using=WEBAPI_DB_ALIAS):
            with get_webapi_connection().cursor() as cursor:
                sec_user_id = _resolve_sec_user_id(cursor, user)
                role_id = ensure_sec_role(cursor, role_name)
                ensure_sec_user_role_link(cursor, sec_user_id, role_id)

        logger.info(f"Granted role '{role_name}' to {user.username} in SEC")
        return True

    except Exception as e:
        logger.exception(f"Failed to grant role '{role_name}' to {user.username}: {e}")
        return False


def revoke_role_from_sec(user, role_name):
    """
    Revoke a single role from a user in SEC.

    Note: Base roles (public, personal) cannot be revoked.

    Args:
        user: Atlas User model instance
        role_name: Name of the role to revoke

    Returns:
        bool: True if successful
    """
    if not SEC_SYNC_ENABLED:
        return True

    # Protect base roles
    login = user.username.lower()
    if role_name.lower() in (PUBLIC_ROLE_NAME, login):
        logger.warning(f"Cannot revoke base role '{role_name}' from {user.username}")
        return False

    try:
        with transaction.atomic(using=WEBAPI_DB_ALIAS):
            with get_webapi_connection().cursor() as cursor:
                sec_user_id = _resolve_sec_user_id(cursor, user)
                role_id = get_sec_role_id(cursor, role_name)
                if role_id:
                    remove_sec_user_role_link(cursor, sec_user_id, role_id)

        logger.info(f"Revoked role '{role_name}' from {user.username} in SEC")
        return True

    except Exception as e:
        logger.exception(f"Failed to revoke role '{role_name}' from {user.username}: {e}")
        return False


def get_user_roles_from_sec(user):
    """
    Fetch a user's current roles from SEC.

    Args:
        user: Atlas User model instance

    Returns:
        list of str: Role names, or empty list if failed
    """
    if not SEC_SYNC_ENABLED:
        return []

    try:
        with get_webapi_connection().cursor() as cursor:
            sec_user_id = _resolve_sec_user_id(cursor, user)
            rows = fetchall_tuples(
                cursor,
                f"""
                SELECT r.name
                FROM {WEBAPI_SCHEMA}.sec_user_role ur
                JOIN {WEBAPI_SCHEMA}.sec_role r ON ur.role_id = r.id
                WHERE ur.user_id = %s
                ORDER BY r.name;
                """,
                [sec_user_id],
            )
        return [row[0] for row in rows]

    except Exception as e:
        logger.exception(f"Failed to fetch roles for {user.username} from SEC: {e}")
        return []


# =============================================================================
# Utility Functions
# =============================================================================

def test_sec_connection():
    """
    Test the connection to SEC tables.

    Returns:
        dict: Connection status and info
    """
    result = {
        'enabled': SEC_SYNC_ENABLED,
        'schema': WEBAPI_SCHEMA,
        'db_alias': WEBAPI_DB_ALIAS,
        'connected': False,
        'role_count': 0,
        'user_count': 0,
        'error': None,
    }

    if not SEC_SYNC_ENABLED:
        return result

    try:
        with get_webapi_connection().cursor() as cursor:
            # Test role table
            result['role_count'] = fetchone_value(
                cursor,
                f"SELECT COUNT(*) FROM {WEBAPI_SCHEMA}.sec_role;"
            ) or 0

            # Test user table
            result['user_count'] = fetchone_value(
                cursor,
                f"SELECT COUNT(*) FROM {WEBAPI_SCHEMA}.sec_user;"
            ) or 0

            result['connected'] = True

    except Exception as e:
        result['error'] = str(e)

    return result
