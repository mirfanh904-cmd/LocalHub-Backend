from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from .serializers import FavouriteServiceSerializer, FavouriteProfessionalSerializer


class FavouriteSchemas:
    toggle_service = extend_schema(
        tags=["Favourites"],
        summary="Toggle Favourite Service",
        description="Adds or removes a service from the authenticated user's favorites list.",
        responses={
            200: OpenApiResponse(description="Toggled successfully."),
            404: OpenApiResponse(description="Service not found."),
        },
        examples=[
            OpenApiExample(
                "Toggle Service Success Response",
                value={"status": "success", "is_favourited": True},
                response_only=True,
            )
        ]
    )

    toggle_professional = extend_schema(
        tags=["Favourites"],
        summary="Toggle Favourite Professional",
        description="Adds or removes a professional from the authenticated user's favorites list.",
        responses={
            200: OpenApiResponse(description="Toggled successfully."),
            404: OpenApiResponse(description="Professional not found."),
        },
        examples=[
            OpenApiExample(
                "Toggle Professional Success Response",
                value={"status": "success", "is_favourited": True},
                response_only=True,
            )
        ]
    )

    list_services = extend_schema(
        tags=["Favourites"],
        summary="List Favourite Services",
        description="Returns all services saved as favorites by the user.",
        responses={
            200: FavouriteServiceSerializer(many=True),
        }
    )

    list_professionals = extend_schema(
        tags=["Favourites"],
        summary="List Favourite Professionals",
        description="Returns all professionals saved as favorites by the user.",
        responses={
            200: FavouriteProfessionalSerializer(many=True),
        }
    )
