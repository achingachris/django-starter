from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from apps.users.helpers import admin_role_required


def offline(request):
    """Fallback page shown by the service worker when there is no network connection."""
    return render(request, "web/offline.html")


def service_worker(request):
    """
    Serve the service worker from the site root so its scope covers the whole app
    (a service worker's scope is limited to the directory it's served from).
    """
    with (settings.BASE_DIR / "static" / "javascript" / "service-worker.js").open() as f:
        content = f.read()
    return HttpResponse(content, content_type="application/javascript")


def home(request):
    if request.user.is_authenticated:
        return render(
            request,
            "web/app_home.html",
            context={
                "active_tab": "dashboard",
                "page_title": _("Dashboard"),
            },
        )
    else:
        return render(request, "web/landing_page.html")


@admin_role_required
def admin_dashboard(request):
    """A simple dashboard only visible to users with the 'Admin' role (or superusers)."""
    User = get_user_model()
    users = User.objects.all().order_by("-date_joined")
    return render(
        request,
        "web/admin_dashboard.html",
        context={
            "active_tab": "admin_dashboard",
            "page_title": _("Admin Dashboard"),
            "users": users,
            "member_count": users.filter(role="member").count(),
            "admin_count": users.filter(role="admin").count(),
        },
    )


@user_passes_test(lambda u: u.is_superuser)
def simulate_error(request):
    raise Exception("This is a simulated error.")
