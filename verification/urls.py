from django.urls import path
from .views import (verification_detail, submit_verification
                    ,upload_document,delete_document,verification_list,verification_admin_detail,
                    approve_verification,reject_verification,mark_under_review,suspend_verification,
                    )
app_name = "verification"

urlpatterns = [
    path("verification/", verification_detail, name="detail"),
    path( "<int:pk>/submit/", submit_verification, name="submit"),
    path("upload/", upload_document, name="upload"),
    path("document/<int:pk>/delete/", delete_document, name="delete_document"),

    path("admin/", verification_list, name="list"),
    path("admin/<int:pk>/", verification_admin_detail, name="admin_detail"),
    path("admin/<int:pk>/approve/", approve_verification, name="approve"),
    path("admin/<int:pk>/reject/", reject_verification, name="reject"),
    path("admin/<int:pk>/under-review/", mark_under_review, name="under_review"),
    path("admin/<int:pk>/suspend/", suspend_verification, name="suspend"),
]
