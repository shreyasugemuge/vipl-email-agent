---
phase: 01-google-oauth-sso
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - requirements.txt
  - config/settings/base.py
  - config/urls.py
  - apps/accounts/models.py
  - apps/accounts/adapters.py
  - apps/accounts/urls.py
  - apps/accounts/views.py
  - apps/accounts/admin.py
  - apps/accounts/migrations/0002_user_avatar_url.py
  - apps/accounts/migrations/0003_set_superuser_emails.py
  - apps/accounts/tests/test_auth.py
  - apps/accounts/tests/test_oauth.py
  - templates/registration/login.html
  - templates/base.html
autonomous: true
requirements: [R1.1, R1.2, R1.3, R1.4, R1.5, R1.6]

must_haves:
  truths:
    - "User sees a 'Sign in with Google' button on the login page"
    - "Google sign-in with @vidarbhainfotech.com account logs the user in and redirects to /emails/"
    - "Google sign-in with @gmail.com or other non-VIPL domain is rejected with a clear error message"
    - "First-time Google sign-in creates an inactive account and shows 'Waiting for admin approval' message"
    - "Existing superuser can still log in with username/password at /accounts/login/?password=1"
    - "Sidebar shows Google avatar and user name for OAuth users"
    - "Post-login shows a welcome toast with first name and avatar"
  artifacts:
    - path: "apps/accounts/adapters.py"
      provides: "VIPLSocialAccountAdapter with domain enforcement + auto-inactive + avatar storage"
      exports: ["VIPLSocialAccountAdapter"]
    - path: "config/settings/base.py"
      provides: "allauth INSTALLED_APPS, MIDDLEWARE, AUTHENTICATION_BACKENDS, SOCIALACCOUNT_PROVIDERS"
      contains: "allauth.socialaccount.providers.google"
    - path: "templates/registration/login.html"
      provides: "Google Sign-In button, hidden password form, domain error display, approval pending message"
    - path: "templates/base.html"
      provides: "Google avatar in sidebar user section, welcome toast"
    - path: "apps/accounts/migrations/0002_user_avatar_url.py"
      provides: "avatar_url field on User model"
    - path: "apps/accounts/migrations/0003_set_superuser_emails.py"
      provides: "Data migration setting email on existing superusers"
  key_links:
    - from: "templates/registration/login.html"
      to: "allauth Google provider"
      via: "{% provider_login_url 'google' %} template tag"
      pattern: "provider_login_url.*google"
    - from: "apps/accounts/adapters.py"
      to: "config/settings/base.py"
      via: "SOCIALACCOUNT_ADAPTER setting"
      pattern: "SOCIALACCOUNT_ADAPTER.*adapters.VIPLSocialAccountAdapter"
    - from: "config/urls.py"
      to: "allauth.urls"
      via: "include('allauth.urls')"
      pattern: "allauth\\.urls"

user_setup:
  - service: google-oauth
    why: "Google Sign-In requires OAuth 2.0 credentials from GCP Console"
    env_vars:
      - name: GOOGLE_OAUTH_CLIENT_ID
        source: "GCP Console -> utilities-vipl project -> APIs & Services -> Credentials -> OAuth 2.0 Client IDs"
      - name: GOOGLE_OAUTH_CLIENT_SECRET
        source: "Same OAuth 2.0 credential as above"
    dashboard_config:
      - task: "Create OAuth consent screen (Internal type)"
        location: "GCP Console -> utilities-vipl -> APIs & Services -> OAuth consent screen"
      - task: "Create OAuth 2.0 Web Application credentials"
        location: "GCP Console -> utilities-vipl -> APIs & Services -> Credentials -> Create Credentials -> OAuth client ID"
      - task: "Add authorized redirect URIs"
        location: "Both https://triage.vidarbhainfotech.com/accounts/google/login/callback/ and http://triage.local/accounts/google/login/callback/"
---

<objective>
Install django-allauth with Google provider, enforce @vidarbhainfotech.com domain server-side, redesign the login page with a Google Sign-In button (password form hidden at ?password=1), auto-create new Google users as inactive pending admin approval, add avatar storage and welcome toast, and ensure existing password login still works for superusers.

Purpose: Replace password friction for a 4-person Google Workspace team with SSO, while maintaining emergency superuser access.
Output: Working Google OAuth login flow with domain restriction, inactive-by-default new users, avatar in sidebar, welcome toast.
</objective>

<execution_context>
@/Users/uge/.claude/get-shit-done/workflows/execute-plan.md
@/Users/uge/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-google-oauth-sso/01-CONTEXT.md
@.planning/research/FEATURES.md
@.planning/research/PITFALLS.md

<interfaces>
<!-- Existing codebase contracts the executor needs -->

From apps/accounts/models.py:
```python
class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Team Member"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    can_see_all_emails = models.BooleanField(default=False)

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN
```

From config/settings/base.py:
```python
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/emails/"
LOGOUT_REDIRECT_URL = "/accounts/login/"
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "django_htmx", "apps.core", "apps.accounts", "apps.emails",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

From config/urls.py:
```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/dashboard/", RedirectView.as_view(url="/emails/", permanent=False), name="dashboard_redirect"),
    path("accounts/", include("apps.accounts.urls")),
    path("emails/", include("apps.emails.urls")),
    path("", include("apps.core.urls")),
    path("", RedirectView.as_view(url="/emails/", permanent=False)),
]
```

From apps/accounts/urls.py:
```python
urlpatterns = [
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
```

From templates/base.html sidebar user section (lines 142-164):
```html
<!-- User section at bottom -->
<div class="px-2.5 py-2.5 border-t border-white/[0.06]">
    {% if user.is_authenticated %}
    <div class="flex items-center gap-2.5 px-2 py-2 rounded-lg hover:bg-white/[0.04] transition-colors">
        <div class="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-400 to-violet-500 flex items-center justify-center text-white text-[10px] font-bold shadow-sm">
            {{ user.first_name.0|default:user.username.0|upper }}
        </div>
        <!-- ... name + logout link ... -->
    </div>
    {% endif %}
</div>
```

From templates/registration/login.html:
- Glass-card design with gradient background
- Error display pattern: red-50 bg, red-100 border, red-600 text, icon + message
- Tailwind v4 CDN + Plus Jakarta Sans
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Install allauth, configure settings, add User.avatar_url, create data migration, build adapter</name>
  <files>
    requirements.txt
    config/settings/base.py
    config/urls.py
    apps/accounts/models.py
    apps/accounts/adapters.py
    apps/accounts/urls.py
    apps/accounts/views.py
    apps/accounts/admin.py
    apps/accounts/migrations/0002_user_avatar_url.py
    apps/accounts/migrations/0003_set_superuser_emails.py
    apps/accounts/tests/test_oauth.py
  </files>
  <behavior>
    - Test: VIPLSocialAccountAdapter.pre_social_login raises ImmediateHttpResponse for @gmail.com email
    - Test: VIPLSocialAccountAdapter.pre_social_login allows @vidarbhainfotech.com email (no exception)
    - Test: VIPLSocialAccountAdapter.pre_social_login checks extra_data hd claim, rejects if hd != vidarbhainfotech.com even when email looks correct
    - Test: New Google user auto-created as is_active=False, role=MEMBER, can_see_all_emails=False
    - Test: Adapter stores avatar_url from Google extra_data picture field on User model
    - Test: Inactive user redirected to login with "pending approval" message (not 500)
    - Test: Admin notification email sent when new user created
    - Test: Password login at /accounts/login/?password=1 still works for existing users
    - Test: Password login at /accounts/login/ (without ?password=1) redirects to Google flow or shows Google button only
    - Test: Existing test_auth.py tests still pass (password login works)
    - Test: Data migration sets email on superusers that have blank email fields
  </behavior>
  <action>
**1. Install django-allauth:**
Add `django-allauth[socialaccount]>=65.15,<66` to `requirements.txt` under a new `# v2.2: Google OAuth SSO` comment. Run `pip install -r requirements.txt`.

**2. Configure settings (config/settings/base.py):**
- Add `'django.contrib.sites'` to INSTALLED_APPS (BEFORE allauth apps)
- Add allauth apps: `'allauth'`, `'allauth.account'`, `'allauth.socialaccount'`, `'allauth.socialaccount.providers.google'`
- Add `SITE_ID = 1` (CRITICAL — allauth requires this)
- Add `'allauth.account.middleware.AccountMiddleware'` to MIDDLEWARE (after `AuthenticationMiddleware`)
- Set AUTHENTICATION_BACKENDS:
  ```python
  AUTHENTICATION_BACKENDS = [
      'django.contrib.auth.backends.ModelBackend',  # Password auth (superuser fallback)
      'allauth.account.auth_backends.AuthenticationBackend',  # allauth
  ]
  ```
- Add allauth configuration:
  ```python
  # allauth settings
  ACCOUNT_EMAIL_VERIFICATION = 'none'  # No email verification loop
  ACCOUNT_LOGIN_METHODS = {'username'}  # Keep username-based password login working
  ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
  SOCIALACCOUNT_EMAIL_AUTHENTICATION = False  # SECURITY: prevent email-matching auto-connect
  SOCIALACCOUNT_AUTO_SIGNUP = True
  SOCIALACCOUNT_ADAPTER = 'apps.accounts.adapters.VIPLSocialAccountAdapter'
  SOCIALACCOUNT_PROVIDERS = {
      'google': {
          'SCOPE': ['profile', 'email', 'openid'],
          'AUTH_PARAMS': {
              'access_type': 'online',
              'hd': 'vidarbhainfotech.com',  # UI hint only — enforced server-side in adapter
          },
          'OAUTH_PKCE_ENABLED': True,
      }
  }
  SOCIALACCOUNT_STORE_TOKENS = False  # We don't need access tokens after login

  # OAuth credentials (from environment)
  GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '')
  GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', '')
  ```

**3. Add allauth URLs (config/urls.py):**
Add `path("accounts/", include("allauth.urls")),` AFTER the existing `path("accounts/", include("apps.accounts.urls"))` line. allauth's URLs include `accounts/google/login/` and `accounts/google/login/callback/` which won't conflict with the existing `accounts/login/` and `accounts/logout/` patterns.

**4. Add avatar_url to User model (apps/accounts/models.py):**
Add field: `avatar_url = models.URLField(max_length=500, blank=True, default='')` with help_text "Google profile photo URL, updated on each login".
Run `python manage.py makemigrations accounts` to generate 0002_user_avatar_url.py.

**5. Create data migration for superuser emails (apps/accounts/migrations/0003_set_superuser_emails.py):**
Create a data migration that sets `email = username + '@vidarbhainfotech.com'` on any User where `is_superuser=True` and `email=''`. This prevents allauth email validation from breaking existing superuser accounts. Use `RunPython` with a reverse operation that is a no-op.

**6. Create VIPLSocialAccountAdapter (apps/accounts/adapters.py):**
```python
import logging
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)
ALLOWED_DOMAIN = 'vidarbhainfotech.com'

class VIPLSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """Enforce @vidarbhainfotech.com domain. Reject all others."""
        extra_data = sociallogin.account.extra_data
        email = extra_data.get('email', '')
        hd = extra_data.get('hd', '')

        # SECURITY: Check both email suffix AND hd claim from Google ID token
        if not email.endswith(f'@{ALLOWED_DOMAIN}') or hd != ALLOWED_DOMAIN:
            logger.warning('OAuth rejected: email=%s hd=%s', email, hd)
            messages.error(request, 'Only @vidarbhainfotech.com accounts can sign in.')
            raise ImmediateHttpResponse(redirect('/accounts/login/?error=domain'))

        # If user exists and is linked, update avatar
        if sociallogin.is_existing:
            user = sociallogin.user
            picture = extra_data.get('picture', '')
            if picture and user.avatar_url != picture:
                user.avatar_url = picture
                user.save(update_fields=['avatar_url'])

    def save_user(self, request, sociallogin, form=None):
        """Auto-create new Google users as inactive MEMBER."""
        user = super().save_user(request, sociallogin, form)
        extra_data = sociallogin.account.extra_data

        # Set VIPL defaults
        user.is_active = False  # Requires admin approval
        user.role = 'member'
        user.can_see_all_emails = False
        user.avatar_url = extra_data.get('picture', '')
        user.save(update_fields=['is_active', 'role', 'can_see_all_emails', 'avatar_url'])

        # Notify admin
        admin_email = getattr(settings, 'ADMIN_EMAIL', os.environ.get('ADMIN_EMAIL', ''))
        if admin_email:
            try:
                send_mail(
                    subject=f'New user signup: {user.email}',
                    message=f'{user.get_full_name()} ({user.email}) signed up via Google SSO.\n\nApprove in Django admin: set is_active=True.',
                    from_email=None,  # Uses DEFAULT_FROM_EMAIL
                    recipient_list=[admin_email],
                    fail_silently=True,
                )
            except Exception:
                logger.exception('Failed to send admin notification for new user %s', user.email)

        # Redirect inactive user to login with message
        messages.info(request, 'Account created. Waiting for admin approval.')
        raise ImmediateHttpResponse(redirect('/accounts/login/?pending=1'))

        return user  # Not reached due to ImmediateHttpResponse, but keeps type checkers happy

    def authentication_error(self, request, provider_id, error=None, exception=None, extra_context=None):
        """Handle OAuth errors gracefully."""
        logger.error('OAuth error: provider=%s error=%s exception=%s', provider_id, error, exception)
        messages.error(request, 'Sign-in failed. Please try again.')
        return redirect('/accounts/login/?error=auth')
```

**7. Update accounts/urls.py:**
Keep existing LoginView and LogoutView. The LoginView serves the password form at `?password=1`. allauth handles the Google flow via its own URL patterns added in config/urls.py.

**8. Update accounts/views.py:**
Add a simple view or modify the login URL handling so that `/accounts/login/` without `?password=1` renders the Google-only login page. The simplest approach: use a custom LoginView subclass that checks for `?password=1` query param and either shows the password form or the Google-only page. Both use the same `registration/login.html` template — the template checks `request.GET.password` to toggle which form to show.

Actually, keep it template-only: the existing `auth_views.LoginView` renders `registration/login.html`. The template itself checks `request.GET.password` to decide whether to show the password form or the Google button. No view changes needed.

**9. Update accounts/admin.py:**
Add `avatar_url` to `list_display` and to the "VIPL Settings" fieldset so admins can see it.

**10. Write tests (apps/accounts/tests/test_oauth.py):**
Write the tests described in the behavior block above. Use `unittest.mock.patch` for the allauth adapter methods. Test the adapter's `pre_social_login` by constructing a mock `sociallogin` object with the appropriate `extra_data`. Test `save_user` similarly. Test the login template renders correctly with and without `?password=1`. Test that the data migration function works.

**Run `python manage.py migrate` to apply all migrations** (allauth tables + avatar_url + superuser emails).
  </action>
  <verify>
    <automated>cd /Users/uge/code/vipl-email-agent && source .venv/bin/activate && pip install -r requirements.txt && python manage.py migrate && pytest apps/accounts/ -v -x</automated>
  </verify>
  <done>
    - django-allauth installed and configured in settings
    - allauth URLs mounted, migrations applied (allauth tables + avatar_url + superuser email fix)
    - VIPLSocialAccountAdapter enforces @vidarbhainfotech.com domain (checks both email and hd claim)
    - New Google users created as inactive with role=MEMBER, admin notified via email
    - Avatar URL stored on User model, updated on each login
    - Password login preserved via existing LoginView
    - All existing tests pass, new adapter tests pass
  </done>
</task>

<task type="auto">
  <name>Task 2: Redesign login page + sidebar avatar + welcome toast</name>
  <files>
    templates/registration/login.html
    templates/base.html
  </files>
  <action>
**1. Redesign login.html:**

Replace the current login template with a dual-mode design:
- **Default mode (no query params, or ?error=domain, or ?pending=1):** Shows ONLY the Google Sign-In button. No password form visible. No divider.
- **Password mode (?password=1):** Shows the existing username/password form. No Google button.

Keep the existing glass-card design aesthetic (gradient-bg, glass-card class, decorative blurred circles, Plus Jakarta Sans).

Template structure:
```html
{% load socialaccount %}
<!DOCTYPE html>
<html lang="en">
<!-- Same head as current: Tailwind CDN, Plus Jakarta Sans, gradient-bg + glass-card styles -->
<body class="gradient-bg font-sans min-h-screen flex items-center justify-center p-4">
    <!-- Same decorative blurred circles -->
    <div class="w-full max-w-[380px] relative z-10">
        <div class="glass-card rounded-2xl shadow-2xl shadow-black/20 border border-white/20 p-9">
            <div class="text-center mb-8">
                <!-- Same icon + heading -->
                <h1 class="text-xl font-extrabold text-slate-900 tracking-tight">Welcome back</h1>
                <p class="text-[13px] text-slate-400 mt-1.5 font-medium">Sign in to VIPL Email Triage</p>
            </div>

            <!-- Error messages -->
            {% if request.GET.error == 'domain' %}
            <div class="mb-5 p-3 bg-red-50 border border-red-100 rounded-xl text-[13px] text-red-600 font-medium flex items-center gap-2.5">
                <div class="w-7 h-7 rounded-lg bg-red-100 flex items-center justify-center shrink-0">
                    <svg class="w-3.5 h-3.5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                </div>
                Only @vidarbhainfotech.com accounts can sign in.
            </div>
            {% endif %}

            {% if request.GET.pending %}
            <div class="mb-5 p-3 bg-blue-50 border border-blue-100 rounded-xl text-[13px] text-blue-600 font-medium flex items-center gap-2.5">
                <div class="w-7 h-7 rounded-lg bg-blue-100 flex items-center justify-center shrink-0">
                    <svg class="w-3.5 h-3.5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                </div>
                Account created. Waiting for admin approval.
            </div>
            {% endif %}

            {% if request.GET.error == 'auth' %}
            <div class="mb-5 p-3 bg-red-50 border border-red-100 rounded-xl text-[13px] text-red-600 font-medium flex items-center gap-2.5">
                <div class="w-7 h-7 rounded-lg bg-red-100 flex items-center justify-center shrink-0">
                    <svg class="w-3.5 h-3.5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                </div>
                Sign-in failed. Please try again.
            </div>
            {% endif %}

            {% if request.GET.password == '1' %}
            <!-- PASSWORD MODE: existing form -->
            {% if form.errors %}
            <div class="mb-5 p-3 bg-red-50 border border-red-100 rounded-xl text-[13px] text-red-600 font-medium flex items-center gap-2.5">
                <!-- same error icon -->
                Invalid username or password.
            </div>
            {% endif %}
            <form method="post" class="space-y-4">
                {% csrf_token %}
                <div>
                    <label for="id_username" class="block text-[11px] font-bold text-slate-500 mb-1.5 uppercase tracking-wider">Username</label>
                    <input type="text" name="username" id="id_username" autofocus
                           class="input-focus w-full px-3.5 py-2.5 bg-slate-50/80 border border-slate-200 rounded-xl text-sm font-medium text-slate-800 focus:outline-none focus:border-indigo-400 transition-all placeholder:text-slate-400"
                           placeholder="Enter your username">
                </div>
                <div>
                    <label for="id_password" class="block text-[11px] font-bold text-slate-500 mb-1.5 uppercase tracking-wider">Password</label>
                    <input type="password" name="password" id="id_password"
                           class="input-focus w-full px-3.5 py-2.5 bg-slate-50/80 border border-slate-200 rounded-xl text-sm font-medium text-slate-800 focus:outline-none focus:border-indigo-400 transition-all placeholder:text-slate-400"
                           placeholder="Enter your password">
                </div>
                <button type="submit" class="w-full py-2.5 px-4 bg-gradient-to-r from-indigo-600 to-violet-600 text-white text-sm font-bold rounded-xl hover:from-indigo-700 hover:to-violet-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:ring-offset-2 transition-all shadow-lg shadow-indigo-500/20 active:scale-[0.98]">
                    Sign in
                </button>
            </form>
            {% else %}
            <!-- GOOGLE MODE: prominent Google button -->
            <a href="{% provider_login_url 'google' %}"
               class="w-full flex items-center justify-center gap-3 py-3 px-4 bg-white border border-slate-200 rounded-xl text-sm font-semibold text-slate-700 hover:bg-slate-50 hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:ring-offset-2 transition-all shadow-sm active:scale-[0.98]">
                <!-- Google multicolor G logo SVG -->
                <svg class="w-5 h-5" viewBox="0 0 24 24">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                Sign in with Google
            </a>
            {% endif %}
        </div>
        <p class="text-center text-[11px] text-indigo-200/30 mt-6 font-semibold tracking-wide">Vidarbha Infotech Private Limited</p>
    </div>
</body>
</html>
```

Important: The `{% load socialaccount %}` tag at the top is required for `{% provider_login_url 'google' %}`.

**2. Update sidebar in base.html (user section, lines ~142-164):**

Replace the hardcoded initials circle with avatar-aware rendering:
```html
<!-- User section at bottom -->
<div class="px-2.5 py-2.5 border-t border-white/[0.06]">
    {% if user.is_authenticated %}
    <div class="flex items-center gap-2.5 px-2 py-2 rounded-lg hover:bg-white/[0.04] transition-colors">
        {% if user.avatar_url %}
        <img src="{{ user.avatar_url }}" alt="" class="w-7 h-7 rounded-full object-cover shadow-sm" referrerpolicy="no-referrer">
        {% else %}
        <div class="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-400 to-violet-500 flex items-center justify-center text-white text-[10px] font-bold shadow-sm">
            {{ user.first_name.0|default:user.username.0|upper }}
        </div>
        {% endif %}
        <div class="flex-1 min-w-0">
            <div class="text-[11px] font-semibold text-slate-200 truncate">{{ user.get_full_name|default:user.username }}</div>
            <div class="text-[9px] text-slate-600 font-medium">{{ user.role|default:"Admin" }}</div>
        </div>
        <a href="{% url 'logout' %}" class="text-slate-600 hover:text-slate-400 transition-colors" title="Logout">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
            </svg>
        </a>
    </div>
    {% endif %}
</div>
```

Note: `referrerpolicy="no-referrer"` is required for Google avatar URLs to load correctly.

**3. Add welcome toast to base.html:**

Add a toast component just before the closing `</body>` tag (inside the `extra_js` block area). Use Django messages framework — the adapter already adds a welcome message via `messages.info`. Add this after the sidebar overlay:

```html
<!-- Welcome toast (shows Django messages) -->
{% if messages %}
{% for message in messages %}
<div id="welcome-toast" class="fixed top-4 right-4 z-[100] flex items-center gap-3 px-4 py-3 bg-white rounded-xl shadow-lg shadow-black/10 border border-slate-200 transform transition-all duration-300 translate-x-0 opacity-100"
     style="animation: toast-in 0.3s ease-out, toast-out 0.3s ease-in 3.5s forwards;">
    {% if user.avatar_url %}
    <img src="{{ user.avatar_url }}" alt="" class="w-8 h-8 rounded-full object-cover" referrerpolicy="no-referrer">
    {% endif %}
    <div>
        <p class="text-sm font-semibold text-slate-800">{{ message }}</p>
    </div>
</div>
{% endfor %}
{% endif %}
```

Add the toast animation CSS in the `<style>` block:
```css
@keyframes toast-in { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
@keyframes toast-out { from { transform: translateX(0); opacity: 1; } to { transform: translateX(100%); opacity: 0; } }
```

Also add JS to remove the toast from DOM after animation completes (4s):
```javascript
setTimeout(function() {
    var toast = document.getElementById('welcome-toast');
    if (toast) toast.remove();
}, 4000);
```

**4. Add welcome message on login:**

The welcome toast message needs to be set on successful login. Add a signal receiver or use allauth's `user_logged_in` signal. The simplest approach: in the adapter's `pre_social_login`, when `sociallogin.is_existing` is True (returning user), add a welcome message:
```python
messages.info(request, f'Welcome, {sociallogin.user.first_name or sociallogin.user.username}!')
```

For password logins, add a similar message via Django's `user_logged_in` signal in `apps/accounts/views.py` or `apps/accounts/signals.py`:
```python
from django.contrib.auth.signals import user_logged_in
from django.contrib import messages

def on_user_logged_in(sender, request, user, **kwargs):
    if not request.session.get('_welcome_shown'):
        first_name = user.first_name or user.username
        messages.info(request, f'Welcome, {first_name}!')
        request.session['_welcome_shown'] = True

user_logged_in.connect(on_user_logged_in)
```

Use `_welcome_shown` session key to show the toast only once per session (not on every page refresh).
  </action>
  <verify>
    <automated>cd /Users/uge/code/vipl-email-agent && source .venv/bin/activate && python manage.py migrate && pytest apps/accounts/ -v -x && python -c "from django.template import engines; e = engines['django']; t = e.from_string('{% load socialaccount %}OK'); print(t.render())"</automated>
  </verify>
  <done>
    - Login page shows Google Sign-In button by default (no password form visible)
    - Password form accessible only at /accounts/login/?password=1
    - Domain error (error=domain), pending approval (pending=1), and auth error (error=auth) messages display correctly in the glass card
    - Google button uses official branded SVG logo (white bg, multicolor G)
    - Sidebar shows Google avatar for OAuth users, initials circle for password users
    - Welcome toast appears on login with user's first name (and avatar if available), auto-dismisses after ~4s
    - Toast only shows once per session
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
    Complete Google OAuth SSO flow: allauth installed and configured, domain enforcement adapter, login page redesigned with Google button (password hidden at ?password=1), sidebar avatar display, welcome toast.
  </what-built>
  <how-to-verify>
    **Pre-requisite:** GCP OAuth credentials must be created first (R1.6). Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET in .env.

    1. Start dev server: `python manage.py runserver 8000`
    2. Visit http://triage.local/accounts/login/
       - Expect: Google Sign-In button only, no password form
    3. Visit http://triage.local/accounts/login/?password=1
       - Expect: Username/password form (existing behavior)
    4. Click "Sign in with Google" button
       - Sign in with your @vidarbhainfotech.com account
       - Expect: Redirected to /emails/, welcome toast with your name and photo
    5. Check sidebar bottom: should show your Google avatar and full name
    6. Log out, try signing in with a non-VIPL Google account (if available)
       - Expect: Redirected to login with "Only @vidarbhainfotech.com accounts can sign in" error
    7. Log out, sign in via password at ?password=1 with existing superuser
       - Expect: Works normally, redirects to /emails/
    8. Run full test suite: `pytest -v`
       - Expect: All tests pass (existing 257 + new OAuth tests)
  </how-to-verify>
  <resume-signal>Type "approved" or describe issues to fix</resume-signal>
</task>

</tasks>

<verification>
- `pytest apps/accounts/ -v` passes all auth + OAuth tests
- `pytest -v` passes all 257+ tests (no regressions)
- `python manage.py migrate` applies cleanly (allauth tables + avatar_url + superuser email fix)
- Login page renders Google button at / and password form at ?password=1
- Non-VIPL domain rejected with error message
- Sidebar shows avatar for OAuth users, initials for password users
</verification>

<success_criteria>
- Google Sign-In works end-to-end for @vidarbhainfotech.com accounts
- Non-VIPL Google accounts are rejected with clear error message
- New users auto-created as inactive, admin notified
- Existing superuser password login works at ?password=1
- Avatar displayed in sidebar, welcome toast on login
- All existing tests pass without modification
</success_criteria>

<output>
After completion, create `.planning/phases/01-google-oauth-sso/01-01-SUMMARY.md`
</output>
