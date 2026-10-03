from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema_view

from api.permissions import IsAdmin
from services.models import ServiceGroup
from services.services import ServiceGroupService
from .serializers import ServiceGroupCRUDSerializer
from .schemas import ServiceGroupSchemas


@extend_schema_view(
    list=ServiceGroupSchemas.list,
    create=ServiceGroupSchemas.create,
    retrieve=ServiceGroupSchemas.retrieve,
    update=ServiceGroupSchemas.update,
    partial_update=ServiceGroupSchemas.partial_update,
    destroy=ServiceGroupSchemas.destroy,
)
class ServiceGroupViewSet(viewsets.ModelViewSet):
    queryset = ServiceGroup.objects.all().order_by("display_order", "name")
    serializer_class = ServiceGroupCRUDSerializer
    permission_classes = [IsAdmin]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["display_order", "name", "created_at"]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        success, message = ServiceGroupService.delete(instance)
        if not success:
            return Response(
                {"status": "error", "message": message},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
