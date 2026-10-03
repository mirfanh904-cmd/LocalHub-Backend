from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from bookings.models import Booking, Review
from bookings.selectors import BookingSelector
from bookings.services import ReviewService, ReviewReplyService, ReviewReportService
from .serializers import (
    ReviewSerializer,
    ReviewCreateSerializer,
    ReviewReplySerializer,
    ReviewReplyCreateSerializer,
    ReviewReportCreateSerializer,
)


class SubmitReviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="submit_booking_review",
        summary="Submit Booking Review",
        description="Submit a rating (1-5) and optional review comment for a completed booking.",
        request=ReviewCreateSerializer,
        responses={
            201: ReviewSerializer,
            400: OpenApiResponse(description="Validation error (booking not completed, already reviewed, or invalid rating)"),
            404: OpenApiResponse(description="Booking not found"),
        },
        tags=["Reviews"],
    )
    def post(self, request, booking_number):
        booking = BookingSelector.customer_detail(booking_number, request.user)
        if not booking:
            return Response(
                {"success": False, "message": "Booking not found or not owned by you."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            review = ReviewService.create_review(
                booking=booking,
                customer=request.user,
                rating=serializer.validated_data["rating"],
                comment=serializer.validated_data.get("comment", "")
            )
            return Response(
                {
                    "success": True,
                    "message": "Review submitted successfully.",
                    "data": ReviewSerializer(review).data,
                },
                status=status.HTTP_201_CREATED
            )
        except (ValueError, ValidationError) as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ServiceReviewListAPIView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="list_service_reviews",
        summary="List Service Reviews",
        description="Returns all customer reviews and professional replies for a given service slug.",
        tags=["Reviews"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        slug = self.kwargs.get("slug")
        return (
            Review.objects
            .filter(service__slug=slug)
            .select_related("customer", "service", "booking", "worker", "reply", "reply__professional")
            .order_by("-created_at")
        )


class ProfessionalReviewListAPIView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="list_professional_reviews",
        summary="List Professional Reviews",
        description="Returns all reviews received by a professional worker.",
        tags=["Reviews"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        professional_id = self.kwargs.get("professional_id")
        return (
            Review.objects
            .filter(worker_id=professional_id)
            .select_related("customer", "service", "booking", "worker", "reply", "reply__professional")
            .order_by("-created_at")
        )


class FeaturedReviewListAPIView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="list_featured_reviews",
        summary="List Featured Reviews",
        description="Returns top high-rated customer reviews across the platform.",
        tags=["Reviews"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return (
            Review.objects
            .filter(rating__gte=4)
            .select_related("customer", "service", "booking", "worker", "reply", "reply__professional")
            .order_by("-rating", "-created_at")[:10]
        )


class ReviewReplyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="reply_to_review",
        summary="Reply to Customer Review",
        description="Allows the assigned professional to post or update an official public response to a customer review.",
        request=ReviewReplyCreateSerializer,
        responses={
            200: ReviewReplySerializer,
            400: OpenApiResponse(description="Validation error"),
            403: OpenApiResponse(description="Not authorized (only the assigned worker can reply)"),
            404: OpenApiResponse(description="Review not found"),
        },
        tags=["Reviews"],
    )
    def post(self, request, pk):
        review = get_object_or_404(Review, id=pk)
        serializer = ReviewReplyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            reply = ReviewReplyService.reply_to_review(
                review=review,
                professional_user=request.user,
                comment=serializer.validated_data["comment"],
            )
            return Response(
                {
                    "success": True,
                    "message": "Reply posted successfully.",
                    "data": ReviewReplySerializer(reply).data,
                },
                status=status.HTTP_200_OK
            )
        except ValidationError as e:
            return Response(
                {"success": False, "message": e.message if hasattr(e, "message") else str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ReviewReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="report_review",
        summary="Report / Flag Inappropriate Review",
        description="Allows authenticated users to flag/report a review for spam, harassment, inappropriate content, or fraud.",
        request=ReviewReportCreateSerializer,
        responses={
            201: OpenApiResponse(description="Review reported successfully"),
            400: OpenApiResponse(description="Validation error or duplicate report"),
            404: OpenApiResponse(description="Review not found"),
        },
        tags=["Reviews"],
    )
    def post(self, request, pk):
        review = get_object_or_404(Review, id=pk)
        serializer = ReviewReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            report = ReviewReportService.report_review(
                review=review,
                reporter_user=request.user,
                reason=serializer.validated_data["reason"],
                description=serializer.validated_data.get("description", ""),
            )
            return Response(
                {
                    "success": True,
                    "message": "Review report submitted. Our Trust & Safety team will review it.",
                },
                status=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return Response(
                {"success": False, "message": e.message if hasattr(e, "message") else str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
