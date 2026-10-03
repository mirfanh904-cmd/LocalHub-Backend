from django.urls import path

from . import views
app_name = "bookings"
urlpatterns = [
    path("", views.my_bookings, name="my_bookings"),
    path("checkout/<slug:slug>/", views.checkout, name="checkout"),
    path("method/<slug:slug>/",views.booking_method, name="booking_method"),
    path("add_address/", views.booking_add_address,name="booking_add_address",),
    path("create/<slug:slug>/",views.create_booking, name="create_booking"),
    path("success/<str:booking_number>/", views.booking_success, name="booking_success"),
    path("rebook/<str:booking_number>/", views.rebook, name="rebook"),  
    path("<str:booking_number>/cancel/", views.cancel_booking, name="cancel_booking"),
    path("<str:booking_number>/review/", views.submit_review, name="submit_review"),

    path("<str:booking_number>/", views.booking_detail, name="booking_detail"),


]