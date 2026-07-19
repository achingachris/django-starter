import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.management.commands.runserver import Command as StaticfilesRunserverCommand
from django.db import OperationalError, ProgrammingError


class Command(StaticfilesRunserverCommand):
    """`runserver` that ensures a development superuser exists.

    On every `runserver`, if the configured dev superuser is missing it is created;
    if it already exists nothing happens (silently skipped). This only runs when
    ``DEBUG`` is true so production is never affected.

    Credentials default to ``admin@example.com`` / ``admin`` and can be overridden
    with the ``DEV_SUPERUSER_EMAIL`` and ``DEV_SUPERUSER_PASSWORD`` environment
    variables.
    """

    def inner_run(self, *args, **options):
        # ``inner_run`` is invoked exactly once per ``runserver`` (in the reloaded
        # worker process, or the main process under ``--noreload``), so this is a
        # safe place to seed the account without double-running it.
        self._ensure_dev_superuser()
        super().inner_run(*args, **options)

    def _ensure_dev_superuser(self):
        # Never auto-create privileged accounts outside local development.
        if not settings.DEBUG:
            return

        email = os.environ.get("DEV_SUPERUSER_EMAIL", "admin@example.com")
        password = os.environ.get("DEV_SUPERUSER_PASSWORD", "admin")

        user_model = get_user_model()
        username_field = user_model.USERNAME_FIELD

        try:
            # The allauth adapter stores the email in the username field, so match on
            # both to reliably detect an existing dev account.
            if user_model.objects.filter(email__iexact=email).exists() or (
                username_field != "email" and user_model.objects.filter(**{f"{username_field}__iexact": email}).exists()
            ):
                return

            create_kwargs = {"email": email, "password": password}
            if username_field != "email":
                create_kwargs[username_field] = email
            user_model.objects.create_superuser(**create_kwargs)
        except (OperationalError, ProgrammingError):
            # Database isn't migrated yet — skip quietly; `make migrate` will set it up.
            self.stdout.write(
                self.style.WARNING("Skipping dev superuser creation: database not ready (run migrations).")
            )
            return

        self.stdout.write(self.style.SUCCESS(f"Created dev superuser '{email}' (password: '{password}')."))
