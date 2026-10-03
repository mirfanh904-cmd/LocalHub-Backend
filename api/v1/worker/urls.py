from django.urls import path
from . import views

app_name = "api_v1_worker"

urlpatterns = [
    path("bookings/", views.WorkerBookingListAPIView.as_view(), name="booking_list"),
    path("bookings/<str:booking_number>/accept/", views.WorkerAcceptBookingAPIView.as_view(), name="accept_booking"),
    path("bookings/<str:booking_number>/reject/", views.WorkerRejectBookingAPIView.as_view(), name="reject_booking"),
    path("bookings/<str:booking_number>/update-status/", views.WorkerUpdateStatusAPIView.as_view(), name="update_status"),
    path("trust-score/", views.WorkerTrustScoreAPIView.as_view(), name="trust_score"),
]
