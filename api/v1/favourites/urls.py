from django.urls import path
from . import views

app_name = "api_v1_favourites"

urlpatterns = [
    path("services/", views.FavouriteServiceListAPIView.as_view(), name="service_list"),
    path("professionals/", views.FavouriteProfessionalListAPIView.as_view(), name="professional_list"),
    path("services/<int:service_id>/toggle/", views.ToggleFavouriteServiceAPIView.as_view(), name="toggle_service"),
    path("professionals/<int:professional_id>/toggle/", views.ToggleFavouriteProfessionalAPIView.as_view(), name="toggle_professional"),
]
