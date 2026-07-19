# What's New in This Project

This repo started from the [django-starter](https://github.com/ChrisDevCode-Technologies/django-starter)
template (a SaaS-Pegasus-based Django starter with allauth, HTMX, Tailwind
v4, Celery, and Docker already wired up). Everything below is what was
added or changed on top of it, and why.

## 1. Complete user flow

The starter already shipped registration, login, and email confirmation
via `django-allauth`. What was added/verified:

- **Password reset**: `allauth`'s reset-by-email flow was already
  templated (`templates/account/password_reset*.html`) — verified it
  works end-to-end (request → email → set new password).
- **Password change**: same — `allauth`'s `account_change_password`
  view/template already existed and is linked from the account menu;
  verified it works for logged-in users.
- **Profile image**: the `CustomUser` model already had an `avatar`
  `FileField` with validation (file type + 5 MB max) and a Gravatar
  fallback (`apps/users/models.py`). Verified upload works via
  `templates/account/profile.html` and `POST /users/profile/upload-image/`.

No changes were needed for the above three — they were already solid.
The only real bug found and fixed: `apps/web/management/commands/runserver.py`
had Python 2 exception syntax (`except OperationalError, ProgrammingError:`),
which is a `SyntaxError` on Python 3 and crashed `manage.py runserver`
immediately, on every environment. Fixed to
`except (OperationalError, ProgrammingError):`.

## 2. Two user types (Admin / Member)

Added a `role` field to `CustomUser` (`apps/users/models.py`):

```python
class UserRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    MEMBER = "member", "Member"

class CustomUser(AbstractUser):
    ...
    role = models.CharField(max_length=16, choices=UserRole.choices, default=UserRole.MEMBER)
```

- Every new signup defaults to `Member`.
- `user.is_admin_role` is `True` for `role == "admin"` **or** Django
  superusers, so your existing `createsuperuser` account also gets admin
  access automatically.
- `apps/users/helpers.py` adds an `admin_role_required` decorator that
  redirects non-admins with a flash message.
- `/admin-dashboard/` (`apps/web/views.py::admin_dashboard`) is a small
  dashboard — visible only to Admins — listing all users, their avatar,
  role, and join date, plus member/admin counts. It's also linked from
  the sidebar nav, but only for admins (`templates/web/components/app_nav_menu_items.html`).
- New management command to promote/demote a user:
  ```bash
  python manage.py set_user_role someone@example.com admin
  ```
- Django admin (`/admin/`) now shows and filters by `role` too.
- Tests: `apps/web/tests/test_admin_dashboard.py` covers that members are
  blocked, admins are allowed, anonymous users are redirected to login,
  and new users default to `Member`.

## 3. Progressive Web App (2 features)

1. **Offline support via a service worker**
   (`static/javascript/service-worker.js`, registered from
   `assets/javascript/pwa.js`): caches static assets (cache-first) and
   falls back to a friendly `/offline/` page for navigations when there's
   no network. Served at `GET /service-worker.js` (not under `/static/`)
   so its scope covers the whole site, not just `/static/`.
2. **Installable app / "Add to Home Screen"**: `site.webmanifest` now has
   a real `name`, `start_url`, and `scope` (it shipped with a valid
   structure but empty `name`/`short_name`, which blocks installability).
   `assets/javascript/pwa.js` also listens for the browser's
   `beforeinstallprompt` event and reveals a custom **"Install App"**
   button in the top nav (`templates/web/components/top_nav.html`)
   instead of relying on the browser's default (often hidden) UI.

Note: installability and service worker registration require HTTPS in
production (`localhost` is exempt for local testing) — see
[DEPLOYMENT.md](./DEPLOYMENT.md).

## 4. Tailwind CSS

Already fully wired in the starter (Tailwind v4 via `@tailwindcss/vite`,
`daisyui` component classes, `tailwind.config.js`). No changes needed —
verified `npm run build` produces the expected hashed CSS/JS bundles and
`collectstatic` picks them up.

## 5. Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for a step-by-step guide to deploy
this project's existing `Dockerfile` + `docker-compose.yml` stack
(Postgres + Redis + gunicorn + Celery) to a plain Ubuntu VPS, with Nginx
+ Let's Encrypt in front for HTTPS.

## 6. Real dashboard instead of the placeholder home page

Replaced the starter's default `templates/web/app_home.html` (rocket-ship
graphic + "You're Signed In! Now go make something great!") with an
actual dashboard, styled around the project's own existing choice of
`IBM Plex Mono` as the site-wide font (set in `assets/styles/site-tailwind.css`)
rather than a generic card-grid look:

- A session header (name, avatar, role badge, join date).
- A terminal-style status panel reporting real account state (auth,
  role, email-verified, last login) as `>` prompt lines.
- Quick-action cards linking to real routes: edit profile, change
  password, and the "Install App" PWA button (relocated here from the
  nav so it has a real home instead of just floating in the header).
- An admin-only callout linking to `/admin-dashboard/`, rendered
  server-side only for users where `is_admin_role` is true — verified
  with `Client()` tests that the markup is absent for Members, not just
  hidden with CSS.

## 7. Verify email + admin role management

- The dashboard's status panel now links straight to allauth's existing
  "manage email" page (`account_email`) when the user's email isn't
  verified yet, so there's a real, one-click way to resend the
  verification email instead of just being told to "check your inbox."
- The admin dashboard's role column is now an actual control: admins
  can change any other user's role from a dropdown right in the table.
  An admin's own row shows a locked, read-only badge instead of the
  form — and this is enforced server-side in `admin_dashboard`
  (`apps/web/views.py`), not just hidden in the template, so a crafted
  POST request can't be used to self-promote or self-demote either.
- New tests: admin changes another user's role, admin cannot change
  their own role, a non-admin can't POST a role change at all, and an
  invalid role value is rejected.

## Files touched

```
apps/users/models.py                              # + UserRole, role field, is_admin_role
apps/users/admin.py                                # show/filter by role
apps/users/helpers.py                              # + admin_role_required decorator
apps/users/migrations/0003_customuser_role.py      # migration for the new field
apps/users/management/commands/set_user_role.py    # new management command
apps/web/views.py                                  # + admin_dashboard, offline, service_worker views
apps/web/urls.py                                   # + routes for the above
apps/web/management/commands/runserver.py          # bugfix: py2 except syntax
apps/web/tests/test_admin_dashboard.py             # new tests
templates/web/admin_dashboard.html                 # new
templates/web/app_home.html                        # rebuilt: real dashboard, not placeholder
templates/web/offline.html                         # new
templates/web/components/app_nav_menu_items.html   # + admin nav link
templates/web/components/top_nav.html              # + install-app button
static/javascript/service-worker.js                # new
static/images/favicons/site.webmanifest            # filled in name/start_url/scope
assets/javascript/pwa.js                           # new (SW registration + install prompt)
assets/javascript/site.js                          # import pwa.js
DEPLOYMENT.md                                       # new
```

## Verifying locally

```bash
uv sync --group dev --group prod
npm install && npm run build
uv run python manage.py migrate
uv run python manage.py test          # 22 tests, all passing
uv run python manage.py runserver
```
