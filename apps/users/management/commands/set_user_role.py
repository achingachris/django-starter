from django.core.management.base import BaseCommand, CommandError

from apps.users.models import CustomUser, UserRole


class Command(BaseCommand):
    help = "Sets the app-level role (admin/member) for the given user."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)
        parser.add_argument("role", type=str, choices=[choice.value for choice in UserRole])

    def handle(self, username, role, **options):
        try:
            user = CustomUser.objects.get(username=username)
        except CustomUser.DoesNotExist:
            raise CommandError(f"No user with username/email {username} found!") from None
        user.role = role
        user.save()
        self.stdout.write(self.style.SUCCESS(f"{username}'s role is now '{role}'."))
