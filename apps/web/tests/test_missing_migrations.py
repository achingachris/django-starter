from io import StringIO

from django.core.management import call_command
from django.test import TestCase


class PendingMigrationsTests(TestCase):
    # This tests that there are no pending database migrations that haven't been added.
    # for more on the approach and motivation, see https://adamj.eu/tech/2024/06/23/django-test-pending-migrations/
    def test_no_pending_migrations(self):
        out = StringIO()
        try:
            call_command(
                "makemigrations",
                check_changes=True,
                stdout=out,
                stderr=StringIO(),
            )
        except SystemExit:  # pragma: no cover
            raise AssertionError("Pending migrations:\n" + out.getvalue()) from None
