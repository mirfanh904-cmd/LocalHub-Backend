from django.urls import path
from .views import ComplaintListCreateAPIView, ComplaintDetailAPIView

urlpatterns = [
    path("", ComplaintListCreateAPIView.as_view(), name="complaint_list_create"),
    path("<str:complaint_number>/", ComplaintDetailAPIView.as_view(), name="complaint_detail"),
]
