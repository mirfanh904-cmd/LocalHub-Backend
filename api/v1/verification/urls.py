from django.urls import path
from .views import (
    MyVerificationAPIView,
    SubmitVerificationAPIView,
    VerificationDocumentListCreateAPIView,
    VerificationDocumentDeleteAPIView,
    VerificationHistoryAPIView,
    SecureDocumentDownloadAPIView,
)

urlpatterns = [
    path("me/", MyVerificationAPIView.as_view(), name="verification_me"),
    path("me/submit/", SubmitVerificationAPIView.as_view(), name="verification_submit"),
    path("me/documents/", VerificationDocumentListCreateAPIView.as_view(), name="verification_documents"),
    path("me/documents/<int:pk>/", VerificationDocumentDeleteAPIView.as_view(), name="verification_document_delete"),
    path("me/history/", VerificationHistoryAPIView.as_view(), name="verification_history"),
    path("documents/<int:pk>/download/", SecureDocumentDownloadAPIView.as_view(), name="verification_document_download"),
]
