from django.urls import path
from .views import (
    BookingCreateAPIView,
    BookingListAPIView,
    BookingDetailAPIView,
    BookingUpdateAPIView,
    BookingCancelAPIView,
    BookingOTPGenerateAPIView,
    BookingOTPVerifyAPIView,
    BookingOTPStatusAPIView,
    BookingRescheduleListCreateAPIView,
    BookingRescheduleRespondAPIView,
)

urlpatterns = [
    path("", BookingListAPIView.as_view(), name="booking_list"),
    path("create/", BookingCreateAPIView.as_view(), name="booking_create"),
    path("<str:booking_number>/", BookingDetailAPIView.as_view(), name="booking_detail"),
    path("<str:booking_number>/update/", BookingUpdateAPIView.as_view(), name="booking_update"),
    path("<str:booking_number>/cancel/", BookingCancelAPIView.as_view(), name="booking_cancel"),
    path("<str:booking_number>/otp/generate/", BookingOTPGenerateAPIView.as_view(), name="booking_otp_generate"),
    path("<str:booking_number>/otp/verify/", BookingOTPVerifyAPIView.as_view(), name="booking_otp_verify"),
    path("<str:booking_number>/otp/status/", BookingOTPStatusAPIView.as_view(), name="booking_otp_status"),
    path("<str:booking_number>/reschedule/", BookingRescheduleListCreateAPIView.as_view(), name="booking_reschedule_list_create"),
    path("<str:booking_number>/reschedule/<int:request_id>/respond/", BookingRescheduleRespondAPIView.as_view(), name="booking_reschedule_respond"),
]