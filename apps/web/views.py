from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect, render


def home(request):
    if request.user.is_authenticated:
        # service marketplace: send each account type to its own dashboard
        if request.user.is_provider:
            return redirect("services:provider_dashboard")
        return redirect("services:client_dashboard")
    else:
        return render(request, "web/landing_page.html")


@user_passes_test(lambda u: u.is_superuser)
def simulate_error(request):
    raise Exception("This is a simulated error.")
