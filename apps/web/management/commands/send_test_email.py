from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sends a test email to the specified address. Useful for testing your email setup."

    def add_arguments(self, parser):
        parser.add_argument("email", type=str)

    def handle(self, email, **options):
        send_mail(
            "Test email",
            "This is a test email from your app.",
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        print(f"Sent a test email to {email}.")
