from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from .serializers import ReviewSerializer, ReviewCreateSerializer


class ReviewSchemas:
    submit_review = extend_schema(
        tags=["Reviews"],
        summary="Submit Booking Review",
        description="Submits a rating (1-5) and feedback comment for a completed booking. Updates Service and ProfessionalProfile rating statistics.",
        request=ReviewCreateSerializer,
        responses={
            201: ReviewSerializer,
            400: OpenApiResponse(description="Invalid rating or booking not eligible for review."),
            404: OpenApiResponse(description="Booking not found."),
        },
        examples=[
            OpenApiExample(
                "Submit Review Request Example",
                value={
                    "rating": 5,
                    "comment": "Excellent service and punctual professional!"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Submit Review Success Response",
                value={
                    "id": 1,
                    "booking_number": "LH-2026-000001",
                    "customer_name": "John Doe",
                    "service_name": "Home Deep Cleaning",
                    "rating": 5,
                    "comment": "Excellent service and punctual professional!",
                    "created_at": "2026-07-22T10:00:00Z"
                },
                response_only=True,
            )
        ]
    )

    list_service_reviews = extend_schema(
        tags=["Reviews"],
        summary="List Service Reviews",
        description="Returns all customer reviews for a given service by slug.",
        responses={
            200: ReviewSerializer(many=True),
        },
        examples=[
            OpenApiExample(
                "Service Reviews List Response",
                value=[
                    {
                        "id": 1,
                        "booking_number": "LH-2026-000001",
                        "customer_name": "Jane Smith",
                        "service_name": "Home Deep Cleaning",
                        "rating": 5,
                        "comment": "Great experience!",
                        "created_at": "2026-07-22T10:00:00Z"
                    }
                ],
                response_only=True,
            )
        ]
    )
