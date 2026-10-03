from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register("", views.ServiceGroupViewSet, basename="service_groups")

urlpatterns = [
    path("", include(router.urls)),
]
