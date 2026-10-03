from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from .serializers import ServiceGroupCRUDSerializer


class ServiceGroupSchemas:
    list = extend_schema(
        tags=["Admin Service Groups"],
        summary="List Service Groups",
        description="Returns all Service Groups for admin management.",
        responses={200: ServiceGroupCRUDSerializer(many=True)}
    )
    create = extend_schema(
        tags=["Admin Service Groups"],
        summary="Create Service Group",
        description="Create a new top-level Service Group.",
        request=ServiceGroupCRUDSerializer,
        responses={201: ServiceGroupCRUDSerializer}
    )
    retrieve = extend_schema(
        tags=["Admin Service Groups"],
        summary="Retrieve Service Group",
        responses={200: ServiceGroupCRUDSerializer}
    )
    update = extend_schema(
        tags=["Admin Service Groups"],
        summary="Update Service Group",
        request=ServiceGroupCRUDSerializer,
        responses={200: ServiceGroupCRUDSerializer}
    )
    partial_update = extend_schema(
        tags=["Admin Service Groups"],
        summary="Partial Update Service Group",
        request=ServiceGroupCRUDSerializer,
        responses={200: ServiceGroupCRUDSerializer}
    )
    destroy = extend_schema(
        tags=["Admin Service Groups"],
        summary="Delete Service Group",
        description="Deletes a Service Group if it has no dependent categories.",
        responses={
            204: OpenApiResponse(description="Deleted successfully."),
            400: OpenApiResponse(description="Cannot delete service group containing categories."),
        }
    )
