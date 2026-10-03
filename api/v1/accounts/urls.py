from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AddressViewSet,
    UserProfileAPIView,
    UserCapabilitiesAPIView,
    BecomeIndividualProAPIView,
    BecomeHealthcareProAPIView,
    BecomeOrganizationAPIView,
)

router = DefaultRouter()
router.register("addresses", AddressViewSet, basename="address")

urlpatterns = [
    path("profile/", UserProfileAPIView.as_view(), name="user_profile"),
    path("capabilities/", UserCapabilitiesAPIView.as_view(), name="user_capabilities"),
    path("become-pro/individual/", BecomeIndividualProAPIView.as_view(), name="become_individual_pro"),
    path("become-pro/healthcare/", BecomeHealthcareProAPIView.as_view(), name="become_healthcare_pro"),
    path("become-pro/organization/", BecomeOrganizationAPIView.as_view(), name="become_organization"),
    path("", include(router.urls)),
]