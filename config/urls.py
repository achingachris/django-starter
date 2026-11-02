"""django-template URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/stable/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.users import api as users_api

urlpatterns = [
    # >>> web
    # The site's pages. Listed first because it also redirects the Django admin login to the main login page.
    path("", include("apps.web.urls")),
    path("users/", include("apps.users.urls")),
    # <<< web
    path(settings.ADMIN_URL, admin.site.urls),
    # With HEADLESS_ONLY, allauth.urls only keeps the routes needed for provider (social login) callbacks.
    path("accounts/", include("allauth.urls")),
    # allauth headless: the JSON auth API (signup, login, sessions, email verification, password reset).
    path("_allauth/", include("allauth.headless.urls")),
    path("api/users/me/", users_api.me, name="api_user_me"),
    # API docs.
    # These endpoints are public by default. To restrict access, pass `permission_classes`
    # to the views below (e.g. `[permissions.IsAdminUser]`), gate on `settings.DEBUG`,
    # or remove them entirely if you don't want to expose your API surface.
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Optional UI - you may wish to remove one of these depending on your preference
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# >>> web
# Add browser reload URL if the middleware is enabled (matches middleware check in settings.py)
if "django_browser_reload.middleware.BrowserReloadMiddleware" in settings.MIDDLEWARE:
    urlpatterns.insert(0, path("__reload__/", include("django_browser_reload.urls")))
# <<< web

if settings.ENABLE_DEBUG_TOOLBAR:
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))
