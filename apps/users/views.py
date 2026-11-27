from allauth.account.models import EmailAddress
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from .forms import CustomUserChangeForm, UploadAvatarForm
from .helpers import require_email_confirmation, user_has_confirmed_email_address
from .models import CustomUser


@login_required
def profile(request):
    if request.method == "POST":
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    form = _save_profile(request, form)
            except IntegrityError:
                # Another account claimed this address between validation and save (unique_user_email_ci).
                request.user.refresh_from_db()
                form.add_error("email", _("This email address is already in use."))
            else:
                messages.success(request, _("Profile successfully saved."))
    else:
        form = CustomUserChangeForm(instance=request.user)
    return render(
        request,
        "account/profile.html",
        {
            "form": form,
            "active_tab": "profile",
            "page_title": _("Profile"),
        },
    )


def _save_profile(request, form):
    """Save a valid profile form and return the form to render next."""
    user = form.save(commit=False)
    user_before_update = CustomUser.objects.get(pk=user.pk)
    email_changed = user_before_update.email != user.email
    need_to_confirm_email = (
        email_changed and require_email_confirmation() and not user_has_confirmed_email_address(user, user.email)
    )
    if need_to_confirm_email:
        new_email = user.email
        # don't change it but instead rely on allauth to send a confirmation email.
        # email will be changed by signal when confirmed
        EmailAddress.objects.add_email(request, user, new_email, confirm=True)
        # revert the email to the original value until confirmation is completed
        user.email = user_before_update.email
        # recreate the form to avoid populating the previous email in the returned page
        form = CustomUserChangeForm(instance=user)
    user.save()

    if email_changed and not need_to_confirm_email:
        # email changed to an address the user already owns; keep allauth's primary
        # EmailAddress in sync (the email_confirmed signal handles the new-email case)
        email_address = EmailAddress.objects.filter(user=user, email__iexact=user.email).first()
        if email_address:
            email_address.set_as_primary()
    return form


@login_required
@require_POST
def upload_profile_image(request):
    user = request.user
    form = UploadAvatarForm(request.POST, request.FILES)
    if form.is_valid():
        user.avatar = request.FILES["avatar"]
        user.save()
        return HttpResponse(_("Success!"))
    else:
        readable_errors = ", ".join(str(error) for key, errors in form.errors.items() for error in errors)
        return JsonResponse(status=400, data={"errors": readable_errors})
