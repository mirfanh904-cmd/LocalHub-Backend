from rest_framework import generics

from .serializers import CategorySerializer
from services.services import CategorySelector
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
)
@extend_schema(
    summary="List Categories",
    description="Returns all active categories.",
    parameters=[
        OpenApiParameter("group", str),
        OpenApiParameter("featured", bool),
        OpenApiParameter("search", str),
    ],
)
class CategoryListAPIView(generics.ListAPIView):

    serializer_class = CategorySerializer

    def get_queryset(self):

        group = self.request.query_params.get("group")
        featured = self.request.query_params.get("featured")
        search = self.request.query_params.get("search")

        if group:
            return CategorySelector.by_service_group(group)

        if featured == "true":
            return CategorySelector.featured()

        if search:
            return CategorySelector.search(search)

        return CategorySelector.all()

@extend_schema(
    summary="Category Detail",
    description="Retrieve category by slug.",
)
class CategoryDetailAPIView(generics.RetrieveAPIView):

    serializer_class = CategorySerializer
    lookup_field = "slug"

    def get_object(self):

        return CategorySelector.by_slug(
            self.kwargs["slug"]
        )