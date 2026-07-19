---
title: I extended a Django starter template with roles, PWA support, and a real deploy — here's what I learned
published: false
tags: django, python, webdev, tailwindcss
---

I was handed a challenge: take an existing Django starter template, add a
complete user flow, a second user type, make the front end installable as
a PWA, and ship it to a live server — in 48 hours. Here's how it went,
including the one bug that would've bitten anyone using this template on
Python 3.

## Starting point

The [django-starter](https://github.com/ChrisDevCode-Technologies/django-starter)
template is a SaaS-Pegasus-flavored Django project: `django-allauth` for
auth, HTMX + Alpine.js for interactivity, Tailwind v4 via `@tailwindcss/vite`,
a custom user model, Celery, and a full Docker Compose production stack
already wired up. It's a genuinely well-built starting point — most of
"build a complete user flow" was actually already done for me.

## What was already there

Digging into `apps/users/`, I found:

- **Registration & login** via `allauth`, with email as the login method
  (not username) — a config choice in `ACCOUNT_LOGIN_METHODS`.
- **Password reset** — the full email-based reset flow, templated.
- **Password change** — for logged-in users, also templated.
- **Profile pictures** — the `CustomUser` model already had an `avatar`
  field with file-type and size validation, plus a Gravatar fallback if
  no avatar was uploaded.

So step one of the brief was mostly a verification exercise: sign up,
confirm email, log out, reset password, log back in, change password,
upload an avatar. All of it worked out of the box.

## The bug nobody would expect

While smoke-testing, `python manage.py runserver` threw an immediate
`SyntaxError`. The starter ships a custom `runserver` command that
auto-creates a dev superuser on boot, and one line was written in
Python 2 syntax:

```python
except OperationalError, ProgrammingError:
```

That's invalid in Python 3 — the correct form parenthesizes multiple
exception types. It's a one-character-class fix, but it's the kind of
thing that silently breaks a project for anyone who clones it fresh,
which is exactly the kind of bug worth catching before it reaches users.

## Adding two user types

The brief asked for at least two user roles. Rather than overload
Django's built-in `is_staff`/`is_superuser` (which are about Django-admin
access, not app-level permissions), I added an explicit `role` field:

```python
class UserRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    MEMBER = "member", "Member"

class CustomUser(AbstractUser):
    role = models.CharField(max_length=16, choices=UserRole.choices, default=UserRole.MEMBER)
```

New signups default to `Member`. A small `admin_role_required` decorator
gates a new `/admin-dashboard/` view that lists all users, their roles,
and basic stats — visible only to Admins (superusers get treated as
admins automatically, too). A management command
(`set_user_role <email> admin`) makes it easy to promote someone from the
CLI.

## Making it a PWA

Two features were enough per the brief, so I focused on the two that
actually matter for a real app:

1. **A service worker for offline support.** Cache-first for static
   assets, network-first with a cached offline fallback page for regular
   navigation. The tricky part: a service worker's scope is limited to
   the URL path it's served from, and this project's static files live
   under `/static/`. Serving the worker from a dedicated view at
   `/service-worker.js` (site root) instead of inside `/static/` was
   necessary to get full-site scope.
2. **A custom install prompt.** The manifest already existed but had
   empty `name`/`short_name` fields — invisible-but-fatal for
   installability checks. After filling those in, I hooked into the
   browser's `beforeinstallprompt` event to show a proper "Install App"
   button in the nav, instead of leaving it to the browser's often-buried
   default UI.

One gotcha worth flagging for anyone doing this: service worker
registration and PWA installability both require HTTPS in production
(`localhost` is the only exception). If you're testing on a bare IP
without TLS, you won't see the install prompt.

## Shipping it

The template already had a production `Dockerfile` and
`docker-compose.yml` (Postgres, Redis, gunicorn, Celery worker + beat),
which made deployment mostly a matter of following the existing design
rather than inventing one. On a fresh Ubuntu VPS: install Docker, clone
the repo, fill in `.env.prod`, `docker compose up -d --build`, then Nginx
+ Certbot for TLS in front of it. The `web` service already runs
migrations and `collectstatic` on boot, so there's no separate deploy
script to write.

## Wrapping up

The biggest lesson here wasn't really about Django — it was about
resisting the urge to rebuild things that already worked. A good starter
template does most of the "complete user flow" work for you; the real
value-add was in the parts it didn't cover (roles, PWA support), fixing
the one bug that would've tripped up every future user, and writing down
what changed and why so the next person doesn't have to reverse-engineer
it.

Repo: (link in the submission)
Live demo: (link in the submission)
