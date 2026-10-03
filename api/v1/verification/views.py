import os
import mimetypes
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from api.permissions import IsProfessional, IsVerificationOwnerOrAdmin
from accounts.models import ProfessionalProfile
from verification.models import (
    ProfessionalVerification,
    ProfessionalVerificationDocument,
    VerificationStatus,
)
from verification.services import VerificationService
from .serializers import (
    VerificationDetailSerializer,
    VerificationDocumentSerializer,
    VerificationDocumentUploadSerializer,
    VerificationHistoryLogSerializer,
)


def _get_or_create_profile(user):
    profile = getattr(user, "professional_profile", None)
    if not profile:
        profile, _ = ProfessionalProfile.objects.get_or_create(
            user=user,
            defaults={
                "professional_title": f"{user.first_name} (Professional)".strip(),
                "bio": "LocalHub service professional.",
            },
        )
    return profile


class MyVerificationAPIView(APIView):
    permission_classes = [IsProfessional]

    @extend_schema(
        operation_id="get_my_verification_status",
        summary="Retrieve Verification Status",
        description="Retrieves current KYC verification status, review details, and uploaded documents for the authenticated professional.",
        responses={
            200: VerificationDetailSerializer,
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Professional role required"),
        },
        tags=["Verification"],
    )
    def get(self, request):
        profile = _get_or_create_profile(request.user)
        verification = VerificationService.get_verification(profile)
        serializer = VerificationDetailSerializer(verification, context={"request": request})
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )


class SubmitVerificationAPIView(APIView):
    permission_classes = [IsProfessional]

    @extend_schema(
        operation_id="submit_professional_verification",
        summary="Submit Professional Verification",
        description="Submits the authenticated professional's verification dossier for admin review. Requires at least one uploaded KYC document.",
        request=None,
        responses={
            200: VerificationDetailSerializer,
            400: OpenApiResponse(description="Validation error (missing documents or invalid status)"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Professional role required"),
        },
        tags=["Verification"],
    )
    def post(self, request):
        profile = _get_or_create_profile(request.user)
        verification = VerificationService.get_verification(profile)
        try:
            verification = VerificationService.submit_for_review(verification, performed_by=request.user)
            serializer = VerificationDetailSerializer(verification, context={"request": request})
            return Response(
                {
                    "success": True,
                    "message": "Verification dossier submitted successfully for administrative review.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response(
                {"success": False, "message": e.message if hasattr(e, "message") else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class VerificationDocumentListCreateAPIView(APIView):
    permission_classes = [IsProfessional]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        operation_id="list_my_verification_documents",
        summary="List Verification Documents",
        description="Returns all KYC documents associated with the authenticated professional's verification.",
        responses={200: VerificationDocumentSerializer(many=True)},
        tags=["Verification"],
    )
    def get(self, request):
        profile = _get_or_create_profile(request.user)
        verification = VerificationService.get_verification(profile)
        documents = VerificationService.get_documents(verification)
        serializer = VerificationDocumentSerializer(documents, many=True, context={"request": request})
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="upload_verification_document",
        summary="Upload KYC Verification Document",
        description="Uploads a government identity or trade qualification document (PDF, JPEG, PNG <= 5MB) for verification.",
        request=VerificationDocumentUploadSerializer,
        responses={
            201: VerificationDocumentSerializer,
            400: OpenApiResponse(description="File validation error (size > 5MB, invalid format, corrupted file)"),
        },
        tags=["Verification"],
    )
    def post(self, request):
        profile = _get_or_create_profile(request.user)
        verification = VerificationService.get_verification(profile)
        serializer = VerificationDocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            doc = VerificationService.upload_document(
                verification=verification,
                document_file=serializer.validated_data["file"],
                document_type=serializer.validated_data["document_type"],
                document_number=serializer.validated_data.get("document_number", ""),
                performed_by=request.user,
            )
            return Response(
                {
                    "success": True,
                    "message": "Document uploaded successfully.",
                    "data": VerificationDocumentSerializer(doc, context={"request": request}).data,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return Response(
                {"success": False, "message": e.message if hasattr(e, "message") else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class VerificationDocumentDeleteAPIView(APIView):
    permission_classes = [IsProfessional]

    @extend_schema(
        operation_id="delete_verification_document",
        summary="Delete Verification Document",
        description="Deletes an uploaded KYC verification document.",
        responses={
            200: OpenApiResponse(description="Document deleted successfully"),
            404: OpenApiResponse(description="Document not found"),
        },
        tags=["Verification"],
    )
    def delete(self, request, pk):
        profile = _get_or_create_profile(request.user)
        doc = get_object_or_404(ProfessionalVerificationDocument, id=pk, verification__professional=profile)
        VerificationService.delete_document(doc, performed_by=request.user)
        return Response(
            {"success": True, "message": "Document deleted successfully."},
            status=status.HTTP_200_OK,
        )


class VerificationHistoryAPIView(APIView):
    permission_classes = [IsProfessional]

    @extend_schema(
        operation_id="get_verification_timeline_history",
        summary="Retrieve Verification History Timeline",
        description="Returns an immutable chronological timeline log of verification lifecycle transitions and actions.",
        responses={200: VerificationHistoryLogSerializer(many=True)},
        tags=["Verification"],
    )
    def get(self, request):
        profile = _get_or_create_profile(request.user)
        verification = VerificationService.get_verification(profile)
        logs = VerificationService.get_history_logs(verification)
        serializer = VerificationHistoryLogSerializer(logs, many=True)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )


class SecureDocumentDownloadAPIView(APIView):
    permission_classes = [IsVerificationOwnerOrAdmin]

    @extend_schema(
        operation_id="download_verification_document",
        summary="Download Private KYC Document",
        description="Streams the private KYC document securely for authorized professionals (owner) or platform administrators. Direct unauthenticated access is prohibited.",
        responses={
            200: OpenApiResponse(description="File stream binary data"),
            403: OpenApiResponse(description="Access forbidden (IDOR protection)"),
            404: OpenApiResponse(description="Document or file not found"),
        },
        tags=["Verification"],
    )
    def get(self, request, pk):
        doc = get_object_or_404(ProfessionalVerificationDocument, id=pk)
        self.check_object_permissions(request, doc)

        if not doc.document_file or not doc.document_file.name:
            raise Http404("Document file does not exist.")

        try:
            file_handle = doc.document_file.open("rb")
        except Exception:
            raise Http404("Document file cannot be opened.")

        content_type, _ = mimetypes.guess_type(doc.document_file.name)
        if not content_type:
            content_type = "application/octet-stream"

        filename = os.path.basename(doc.document_file.name)
        response = FileResponse(file_handle, content_type=content_type)
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response
