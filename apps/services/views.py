"""
Service marketplace views.

Providers manage their service listings and act on incoming bookings;
clients browse the marketplace, book services and manage their appointments.
Most mutating endpoints are HTMX-friendly: forms are returned as modal
partials and successful actions either swap a row or trigger a page refresh.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from .forms import BookingForm, ServiceForm
from .models import Booking, Service


def role_required(user_type):
    """Require an authenticated user of the given CustomUser.UserType value."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.user_type != user_type:
                messages.error(request, _("That page is not available for your account type."))
                return redirect("web:home")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


provider_required = role_required("PROVIDER")
client_required = role_required("CLIENT")


def _refresh_response(message=None, request=None, level=messages.success):
    """Tell HTMX to reload the page (used after modal form success)."""
    if message is not None and request is not None:
        level(request, message)
    response = HttpResponse(status=204)
    response["HX-Refresh"] = "true"
    return response


# ---------------------------------------------------------------------------
# Provider: dashboard, service CRUD, incoming bookings
# ---------------------------------------------------------------------------


@provider_required
def provider_dashboard(request):
    bookings = Booking.objects.filter(service__provider=request.user).select_related("service", "client")
    now = timezone.now()
    context = {
        "active_tab": "provider_dashboard",
        "page_title": _("Provider Dashboard"),
        "pending_bookings": bookings.filter(status=Booking.Status.PENDING, scheduled_at__gte=now)[:8],
        "upcoming_bookings": bookings.filter(
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED], scheduled_at__gte=now
        )[:10],
        "stats": {
            "services": request.user.services.count(),
            "pending": bookings.filter(status=Booking.Status.PENDING, scheduled_at__gte=now).count(),
            "upcoming": bookings.filter(status=Booking.Status.CONFIRMED, scheduled_at__gte=now).count(),
            "completed": bookings.filter(status=Booking.Status.COMPLETED).count(),
        },
    }
    return render(request, "services/provider_dashboard.html", context)


@provider_required
def service_list(request):
    return render(
        request,
        "services/service_list.html",
        {
            "active_tab": "services",
            "page_title": _("My Services"),
            "services": request.user.services.all(),
        },
    )


def _service_modal_response(request, form, service=None):
    return render(
        request,
        "services/partials/service_form_modal.html",
        {"form": form, "service": service},
    )


@provider_required
def service_create(request):
    if request.method == "POST":
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.provider = request.user
            service.save()
            return _refresh_response(_("Service “%(title)s” created.") % {"title": service.title}, request)
        return _service_modal_response(request, form)

    return _service_modal_response(request, ServiceForm())


@provider_required
def service_update(request, pk):
    service = get_object_or_404(Service, pk=pk, provider=request.user)
    if request.method == "POST":
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            return _refresh_response(_("Service updated."), request)
        return _service_modal_response(request, form, service)

    return _service_modal_response(request, ServiceForm(instance=service), service)


@provider_required
@require_POST
def service_toggle_active(request, pk):
    service = get_object_or_404(Service, pk=pk, provider=request.user)
    service.active = not service.active
    service.save(update_fields=["active", "updated_at"])
    state = _("shown in the marketplace") if service.active else _("hidden from the marketplace")
    messages.success(request, _("“%(title)s” is now %(state)s.") % {"title": service.title, "state": state})
    return _refresh_response()


@provider_required
@require_POST
def service_delete(request, pk):
    service = get_object_or_404(Service, pk=pk, provider=request.user)
    if service.bookings.filter(status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED]).exists():
        messages.error(
            request,
            _("“%(title)s” has upcoming bookings and can't be deleted - deactivate it instead.")
            % {"title": service.title},
        )
        return _refresh_response()
    service.delete()
    messages.success(request, _("Service deleted."))
    return _refresh_response()


@provider_required
def provider_bookings(request):
    status_filter = request.GET.get("status", "")
    bookings = (
        Booking.objects.filter(service__provider=request.user)
        .select_related("service", "client")
        .order_by("-scheduled_at")
    )
    if status_filter in Booking.Status.values:
        bookings = bookings.filter(status=status_filter)
    paginator = Paginator(bookings, 15)
    return render(
        request,
        "services/provider_bookings.html",
        {
            "active_tab": "provider_bookings",
            "page_title": _("Bookings"),
            "page_obj": paginator.get_page(request.GET.get("page")),
            "status_filter": status_filter,
            "statuses": Booking.Status.choices,
        },
    )


@provider_required
def booking_detail(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related("service", "client"), pk=pk, service__provider=request.user
    )
    return render(
        request,
        "services/booking_detail.html",
        {
            "active_tab": "provider_bookings",
            "page_title": _("Booking details"),
            "booking": booking,
        },
    )


@provider_required
@require_POST
def booking_set_status(request, pk, new_status):
    booking = get_object_or_404(
        Booking.objects.select_related("service", "client"), pk=pk, service__provider=request.user
    )
    try:
        booking.set_status(new_status)
    except Exception as exc:  # invalid transition
        messages.error(request, str(exc.messages[0] if hasattr(exc, "messages") else exc))
    else:
        messages.success(
            request,
            _("Booking for %(title)s is now %(status)s.")
            % {"title": booking.service.title, "status": booking.get_status_display()},
        )
    if request.htmx:
        # re-render just the affected row
        return render(request, "services/partials/booking_row.html", {"booking": booking, "role": "provider"})
    next_url = request.POST.get("next")
    if next_url and next_url.startswith("/"):
        return redirect(next_url)
    return redirect("services:provider_bookings")


# ---------------------------------------------------------------------------
# Client: dashboard, browse, book, manage bookings
# ---------------------------------------------------------------------------


@client_required
def client_dashboard(request):
    now = timezone.now()
    bookings = request.user.bookings.select_related("service", "service__provider")
    context = {
        "active_tab": "client_dashboard",
        "page_title": _("Client Dashboard"),
        "upcoming_bookings": bookings.filter(
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED], scheduled_at__gte=now
        )[:6],
        "recent_services": Service.objects.filter(active=True).select_related("provider")[:4],
        "stats": {
            "upcoming": bookings.filter(
                status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED], scheduled_at__gte=now
            ).count(),
            "completed": bookings.filter(status=Booking.Status.COMPLETED).count(),
        },
    }
    return render(request, "services/client_dashboard.html", context)


@client_required
def service_browse(request):
    services = Service.objects.filter(active=True).select_related("provider")
    query = request.GET.get("q", "").strip()
    if query:
        services = services.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(provider__first_name__icontains=query)
            | Q(provider__last_name__icontains=query)
        )
    paginator = Paginator(services, 9)
    context = {
        "active_tab": "browse",
        "page_title": _("Browse Services"),
        "page_obj": paginator.get_page(request.GET.get("page")),
        "query": query,
    }
    if request.htmx:
        return render(request, "services/partials/service_cards.html", context)
    return render(request, "services/service_browse.html", context)


@client_required
def service_detail(request, pk):
    service = get_object_or_404(Service.objects.select_related("provider"), pk=pk, active=True)
    if request.method == "POST":
        form = BookingForm(request.POST, service=service)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.client = request.user
            booking.service = service
            booking.save()
            messages.success(
                request,
                _("Booked “%(title)s” for %(when)s. The provider will confirm shortly.")
                % {"title": service.title, "when": booking.scheduled_at.strftime("%b %d, %Y %H:%M")},
            )
            return redirect("services:my_bookings")
    else:
        form = BookingForm(service=service)
    return render(
        request,
        "services/service_detail.html",
        {
            "active_tab": "browse",
            "page_title": service.title,
            "service": service,
            "form": form,
        },
    )


@client_required
def my_bookings(request):
    now = timezone.now()
    bookings = request.user.bookings.select_related("service", "service__provider")
    upcoming = bookings.filter(status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED], scheduled_at__gte=now)
    history = bookings.exclude(pk__in=upcoming).order_by("-scheduled_at")
    return render(
        request,
        "services/my_bookings.html",
        {
            "active_tab": "my_bookings",
            "page_title": _("My Bookings"),
            "upcoming": upcoming,
            "history": history,
        },
    )


@client_required
@require_POST
def booking_cancel(request, pk):
    booking = get_object_or_404(Booking.objects.select_related("service"), pk=pk, client=request.user)
    if not booking.can_cancel:
        messages.error(request, _("This booking can no longer be cancelled."))
    else:
        booking.set_status(Booking.Status.CANCELLED)
        messages.success(request, _("Booking cancelled."))
    if request.htmx:
        return render(request, "services/partials/booking_row.html", {"booking": booking, "role": "client"})
    return redirect("services:my_bookings")


# ---------------------------------------------------------------------------
# HTTP cron endpoint (used by Vercel Cron Jobs - see vercel.json)
# ---------------------------------------------------------------------------
from django.views.decorators.http import require_GET  # noqa: E402


@require_GET
def booking_reminders_cron(request):
    """
    Trigger the booking-reminder task over HTTP.

    Vercel Cron sends ``Authorization: Bearer <CRON_SECRET>`` when the
    ``CRON_SECRET`` env var is set; we verify it here. In DEBUG the secret
    check is skipped so you can just hit the URL from a browser.
    """
    from django.conf import settings

    secret = getattr(settings, "CRON_SECRET", "") or ""
    if secret:
        expected = f"Bearer {secret}"
        if request.headers.get("Authorization", "") != expected:
            return JsonResponse({"detail": "Forbidden"}, status=403)
    elif not settings.DEBUG:
        return JsonResponse({"detail": "CRON_SECRET is not configured"}, status=403)

    from .tasks import send_booking_reminders

    sent = send_booking_reminders()
    return JsonResponse({"reminders": sent})
