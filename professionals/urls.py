from django.urls import path
from .views import  professional_list, professional_detail

urlpatterns = [
    path("<slug:service_slug>/", professional_list, name="professional_list"),
    path("<slug:service_slug>/<uuid:professional_id>/",professional_detail, name="professional_detail")
]