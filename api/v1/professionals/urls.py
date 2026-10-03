from django.urls import path
from .views import (
    ProfessionalListAPIView,
    FeaturedProfessionalsAPIView,
    ProfessionalDetailAPIView,
    ProfessionalTrustScoreAPIView,
)

urlpatterns = [
    path("", ProfessionalListAPIView.as_view(), name="professional_list"),
    path("featured/", FeaturedProfessionalsAPIView.as_view(), name="professional_featured"),
    path("<int:pk>/", ProfessionalDetailAPIView.as_view(), name="professional_detail"),
    path("<int:pk>/trust-score/", ProfessionalTrustScoreAPIView.as_view(), name="professional_trust_score"),
]
