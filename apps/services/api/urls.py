from rest_framework.routers import DefaultRouter

from .views import BookingViewSet, ServiceViewSet

app_name = "services_api"
router = DefaultRouter()
router.register("services", ServiceViewSet, basename="service")
router.register("bookings", BookingViewSet, basename="booking")

urlpatterns = router.urls
