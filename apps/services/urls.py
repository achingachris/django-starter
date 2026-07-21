from django.urls import path

from . import views

app_name = "services"
urlpatterns = [
    # provider
    path("dashboard/provider/", views.provider_dashboard, name="provider_dashboard"),
    path("manage/", views.service_list, name="service_list"),
    path("manage/new/", views.service_create, name="service_create"),
    path("manage/<int:pk>/edit/", views.service_update, name="service_update"),
    path("manage/<int:pk>/toggle/", views.service_toggle_active, name="service_toggle_active"),
    path("manage/<int:pk>/delete/", views.service_delete, name="service_delete"),
    path("incoming/", views.provider_bookings, name="provider_bookings"),
    path("incoming/<int:pk>/", views.booking_detail, name="booking_detail"),
    path("incoming/<int:pk>/status/<str:new_status>/", views.booking_set_status, name="booking_set_status"),
    # client
    path("dashboard/client/", views.client_dashboard, name="client_dashboard"),
    path("browse/", views.service_browse, name="service_browse"),
    path("<int:pk>/", views.service_detail, name="service_detail"),
    path("bookings/", views.my_bookings, name="my_bookings"),
    path("bookings/<int:pk>/cancel/", views.booking_cancel, name="booking_cancel"),
]
