from drf_spectacular.utils import extend_schema, OpenApiResponse
from .serializers import CategoryCRUDSerializer


class CategorySchemas:
    list = extend_schema(
        tags=["Admin Categories"],
        summary="List Categories (Admin)",
        description="Returns all categories for admin CRUD management.",
        responses={200: CategoryCRUDSerializer(many=True)}
    )
    create = extend_schema(
        tags=["Admin Categories"],
        summary="Create Category",
        description="Create a new category linked to a Service Group.",
        request=CategoryCRUDSerializer,
        responses={201: CategoryCRUDSerializer}
    )
    retrieve = extend_schema(
        tags=["Admin Categories"],
        summary="Retrieve Category",
        responses={200: CategoryCRUDSerializer}
    )
    update = extend_schema(
        tags=["Admin Categories"],
        summary="Update Category",
        request=CategoryCRUDSerializer,
        responses={200: CategoryCRUDSerializer}
    )
    partial_update = extend_schema(
        tags=["Admin Categories"],
        summary="Partial Update Category",
        request=CategoryCRUDSerializer,
        responses={200: CategoryCRUDSerializer}
    )
    destroy = extend_schema(
        tags=["Admin Categories"],
        summary="Delete Category",
        description="Deletes a category if it has no active child services.",
        responses={
            204: OpenApiResponse(description="Deleted successfully."),
            400: OpenApiResponse(description="Cannot delete category containing services."),
        }
    )
