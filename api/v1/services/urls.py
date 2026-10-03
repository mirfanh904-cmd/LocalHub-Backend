from django.urls import path
from .views import (
    PlatformStatsAPIView,
    ServiceGroupListAPIView,
    ServiceGroupDetailAPIView,
    ServiceListAPIView,
    FeaturedServiceListAPIView,
    ServiceDetailAPIView,
)

urlpatterns = [
    path("", ServiceListAPIView.as_view(), name="service_list"),
    path("stats/", PlatformStatsAPIView.as_view(), name="platform_stats"),
    path("featured/", FeaturedServiceListAPIView.as_view(), name="service_featured"),
    path("groups/", ServiceGroupListAPIView.as_view(), name="service_group_list"),
    path("groups/<slug:slug>/", ServiceGroupDetailAPIView.as_view(), name="service_group_detail"),
    path("<slug:slug>/", ServiceDetailAPIView.as_view(), name="service_detail"),
]