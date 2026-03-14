# Phase 1: Google OAuth SSO - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Add Google Sign-In to the login page, domain-locked to @vidarbhainfotech.com. Preserve password login as a hidden fallback for superuser emergency access. Auto-create new users on first sign-in but require admin approval before they can access the dashboard.

</domain>

<decisions>
## Implementation Decisions

### Login page layout
- Google-only login: prominent "Sign in with Google" button using Google's official branded style (white background, multicolor G logo)
- No password form visible by default — no divider, no "or" section
- Password form only accessible at `/accounts/login/?password=1` (hidden URL for superuser emergency access)
- Maintain the existing glass-card design aesthetic

### Domain error handling
- Non-VIPL Google accounts (e.g. @gmail.com) redirect back to login page with error message: "Only @vidarbhainfotech.com accounts can sign in"
- Same error style as existing invalid credentials error (red banner in glass card)

### New user flow
- Auto-create account on first Google sign-in: `role=MEMBER`, `can_see_all_emails=False`, `is_active=False`
- User redirected back to login page with banner: "Account created. Waiting for admin approval."
- Admin notified via email to ADMIN_EMAIL (shreyas@vidarbhainfotech.com) — "New user X@vidarbhainfotech.com signed up, approve in Django admin"
- Admin activates user by setting `is_active=True` in Django admin
- Defaults: `can_see_all_emails=False`, `role=MEMBER` — admin adjusts permissions after activation

### Post-login experience
- Redirect to `/emails/` dashboard (same as current LOGIN_REDIRECT_URL)
- Welcome toast on first login of each session: "Welcome, [First Name]!" with Google profile photo
- Toast auto-dismisses after 3-4 seconds
- Store Google avatar URL from OAuth response (on each login, keep fresh)

### User avatar in sidebar
- Show Google avatar + user's name in the sidebar bottom area
- Avatar URL stored from Google's OAuth `extra_data` on each login
- Fallback: initials circle if no avatar available

### Claude's Discretion
- Toast animation and positioning
- Avatar storage approach (User model field vs session)
- Exact allauth configuration details
- Error page styling details
- Email notification template/format

</decisions>

<specifics>
## Specific Ideas

- Login should feel like a modern SaaS login — Google button is THE way to sign in, password is a hidden escape hatch
- The Google button should follow Google's branding guidelines (white, official logo)
- Welcome toast should feel personal — photo + first name, not "Welcome, user"

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `templates/registration/login.html`: Glass-card design with gradient background, already has error display pattern
- `apps/accounts/models.py:User`: Custom AbstractUser with `role` (ADMIN/MEMBER) and `can_see_all_emails` fields
- `apps/emails/services/chat_notifier.py`: Existing notification infrastructure (not used for this — email notification instead)

### Established Patterns
- Django auth views at `apps/accounts/urls.py` — `LoginView` and `LogoutView`
- `LOGIN_REDIRECT_URL = "/emails/"` in `config/settings/base.py`
- HTMX for dynamic UI updates (toast could use HTMX or vanilla JS)
- Tailwind CSS v4 CDN with `@theme` block in templates

### Integration Points
- `config/settings/base.py`: INSTALLED_APPS, MIDDLEWARE, AUTHENTICATION_BACKENDS need allauth additions
- `config/urls.py`: Add allauth URL patterns
- `apps/accounts/adapters.py` (NEW): VIPLSocialAccountAdapter for domain enforcement + auto-create-inactive logic
- `apps/accounts/models.py:User`: May need `avatar_url` field for Google profile photo
- GCP Console: OAuth 2.0 credentials in `utilities-vipl` project (manual step)

</code_context>

<deferred>
## Deferred Ideas

- Permission templates for new users (role presets like "viewer", "handler", "manager") — future phase, user management improvement
- UI/UX guided walkthrough/tutorial overlay for first-time users — future phase, onboarding experience

</deferred>

---

*Phase: 01-google-oauth-sso*
*Context gathered: 2026-03-14*
