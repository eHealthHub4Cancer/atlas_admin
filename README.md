# Atlas Config

A modern, secure, and responsive management system built with Django, Bootstrap 5, and HTMX.

## Features

- **Modern UI/UX**: Clean Bootstrap 5 admin dashboard with responsive design
- **Role-Based Access Control (RBAC)**: Three-tier role system (user, admin, super_admin)
- **Authentication**: Secure login, signup, password reset with bcrypt hashing
- **User Management**: Comprehensive admin interface for managing users and admins
- **Audit Logging**: Complete audit trail of all system actions
- **Email Notifications**: Async email delivery via Celery/Redis
- **Docker Support**: Full containerization with local and external PostgreSQL support

## Tech Stack

- **Backend**: Django 5.1 + Django REST Framework
- **Frontend**: Django Templates + Bootstrap 5 + HTMX
- **Database**: PostgreSQL
- **Task Queue**: Celery + Redis
- **Server**: Gunicorn + WhiteNoise

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### Local Development (with Docker)

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd atlas_admin
   ```

2. **Create environment file**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set your configuration, especially:
   - `DJANGO_SECRET_KEY` - Generate a secure key
   - `SUPER_ADMIN_EMAIL` - Email for initial admin
   - `SUPER_ADMIN_PASSWORD` - Password for initial admin

3. **Start the application**

   ```bash
   docker compose up --build
   ```

4. **Run migrations and seed admin**

   ```bash
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py seed_super_admin
   ```

5. **Access the application**

   - Web App: http://localhost:8000
   - MailHog (dev email): http://localhost:8025 (if using `--profile dev`)

### External PostgreSQL

To connect to an external PostgreSQL database (RDS, Azure, Supabase, etc.):

1. **Configure environment**

   ```bash
   # In .env
   DB_MODE=external
   DB_HOST=your-database-host.example.com
   DB_PORT=5432
   DB_NAME=atlas_config
   DB_USER=your_username
   DB_PASSWORD=your_secure_password
   DB_SSL=true
   DB_SSLMODE=require
   ```

2. **Start with external database**

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.external.yml up --build
   ```

## Environment Variables

### Core Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | (required) |
| `DJANGO_DEBUG` | Debug mode | `false` |
| `DJANGO_ALLOWED_HOSTS` | Allowed hosts | `localhost,127.0.0.1` |

### Database

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_MODE` | `local` or `external` | `local` |
| `DB_HOST` | Database host | `db` |
| `DB_PORT` | Database port | `5432` |
| `DB_NAME` | Database name | `atlas_config` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | (required) |
| `DB_SSL` | Enable SSL | `false` |
| `DB_SSLMODE` | SSL mode | `prefer` |

### Email

| Variable | Description | Default |
|----------|-------------|---------|
| `EMAIL_BACKEND` | `smtp` or `console` | `console` |
| `EMAIL_HOST` | SMTP host | `smtp.example.com` |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_USE_TLS` | Use TLS | `true` |
| `EMAIL_HOST_USER` | SMTP username | |
| `EMAIL_HOST_PASSWORD` | SMTP password | |
| `EMAIL_FROM_ADDRESS` | From address | `noreply@ehealth4cancer.ie` |

### Super Admin Seeding

| Variable | Description |
|----------|-------------|
| `SUPER_ADMIN_EMAIL` | Initial admin email |
| `SUPER_ADMIN_PASSWORD` | Initial admin password |
| `SUPER_ADMIN_FIRST_NAME` | Admin first name |
| `SUPER_ADMIN_LAST_NAME` | Admin last name |

## Role-Based Access Control

### Roles

| Role | Description |
|------|-------------|
| `user` | Standard user with basic access |
| `admin` | Administrator with user management access |
| `super_admin` | Full system access including role management |

### Permission Rules

- **Users**: Can view and update their own profile
- **Admins**: Can view all users, access admin dashboard
- **Super Admins**: Can promote/demote users, manage all accounts

### Strict Enforcement

- Only `super_admin` can promote users to `admin` or `super_admin`
- Only `super_admin` can demote admins to regular users
- The last `super_admin` cannot be demoted
- All permissions are enforced server-side

## Management Commands

```bash
# Run migrations
docker compose exec web python manage.py migrate

# Create super admin
docker compose exec web python manage.py seed_super_admin

# Create super admin with custom credentials
docker compose exec web python manage.py seed_super_admin --email=admin@example.com --password=SecurePassword123

# Migrate and seed in one command
docker compose exec web python manage.py migrate_and_seed

# Collect static files
docker compose exec web python manage.py collectstatic --noinput
```

## Email Testing

For development, use MailHog to capture emails:

```bash
docker compose --profile dev up
```

Then access MailHog at http://localhost:8025

For production, configure SMTP settings in `.env`.

## Project Structure

```
atlas_admin/
├── accounts/               # Main Django app
│   ├── management/        # Management commands
│   ├── migrations/        # Database migrations
│   ├── templates/         # HTML templates
│   ├── forms.py          # Form definitions
│   ├── models.py         # Database models
│   ├── tasks.py          # Celery tasks
│   ├── urls.py           # URL routing
│   └── views.py          # View functions
├── lifehub/               # Django project settings
│   ├── celery.py         # Celery configuration
│   ├── settings.py       # Django settings
│   └── urls.py           # Root URL configuration
├── static/                # Static files (CSS, JS)
├── templates/             # Global templates
│   ├── emails/           # Email templates
│   └── errors/           # Error pages
├── docker-compose.yml     # Docker Compose (local DB)
├── docker-compose.external.yml  # External DB override
├── Dockerfile            # Web application
├── Dockerfile.worker     # Celery worker
├── .env.example          # Environment template
└── requirements.txt      # Python dependencies
```

## Security Considerations

- All passwords are hashed using bcrypt
- CSRF protection on all forms
- Session-based authentication
- Server-side RBAC enforcement (not just UI)
- Audit logging of all sensitive actions
- No secrets in version control

## Support

For questions or issues, contact:

- akwuru.david@ul.ie
- akintomide.jeremiah@ul.ie
- ehealth@ul.ie

---

**ehealthhub4cancer** | https://ehealth4cancer.ie
