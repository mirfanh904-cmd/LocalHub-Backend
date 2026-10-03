from django.urls import path
from .views import (
    SubmitReviewAPIView,
    ServiceReviewListAPIView,
    ProfessionalReviewListAPIView,
    FeaturedReviewListAPIView,
    ReviewReplyAPIView,
    ReviewReportAPIView,
)

urlpatterns = [
    path("featured/", FeaturedReviewListAPIView.as_view(), name="review_featured_list"),
    path("service/<slug:slug>/", ServiceReviewListAPIView.as_view(), name="service_review_list"),
    path("professional/<int:professional_id>/", ProfessionalReviewListAPIView.as_view(), name="professional_review_list"),
    path("booking/<str:booking_number>/", SubmitReviewAPIView.as_view(), name="submit_booking_review"),
    path("<int:pk>/reply/", ReviewReplyAPIView.as_view(), name="review_reply"),
    path("<int:pk>/report/", ReviewReportAPIView.as_view(), name="review_report"),
]
