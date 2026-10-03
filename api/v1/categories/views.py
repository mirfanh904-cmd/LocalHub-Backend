from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema_view

from api.permissions import IsAdmin
from services.models import Category
from services.services import CategoryService
from .serializers import CategoryCRUDSerializer
from .schemas import CategorySchemas


@extend_schema_view(
    list=CategorySchemas.list,
    create=CategorySchemas.create,
    retrieve=CategorySchemas.retrieve,
    update=CategorySchemas.update,
    partial_update=CategorySchemas.partial_update,
    destroy=CategorySchemas.destroy,
)
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by("display_order", "name")
    serializer_class = CategoryCRUDSerializer
    permission_classes = [IsAdmin]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "description", "service_group__name"]
    ordering_fields = ["display_order", "name", "created_at"]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        success, message = CategoryService.delete(instance)
        if not success:
            return Response(
                {"status": "error", "message": message},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
