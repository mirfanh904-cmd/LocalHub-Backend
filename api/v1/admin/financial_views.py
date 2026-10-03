from decimal import Decimal
from django.db.models import Sum
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from api.permissions import IsAdmin
from payments.models import (
    Payment,
    RefundRequest,
    ProfessionalPayout,
    CommissionRecord,
    EscrowHold,
    EscrowStatus,
    PromoCode,
)
from payments.services import RefundService, PayoutService
from payments.models.wallet import WalletTransaction
from api.v1.payments.serializers import (
    PaymentSerializer,
    RefundRequestSerializer,
    ProfessionalPayoutSerializer,
    WalletTransactionSerializer,
)
from .financial_serializers import (
    AdminFinancialOverviewSerializer,
    AdminRefundActionSerializer,
    AdminPayoutActionSerializer,
    AdminPromoCodeSerializer,
)


class AdminFinancialOverviewAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["Admin - Financials"],
        summary="Platform financial metrics and revenue overview",
        responses={200: AdminFinancialOverviewSerializer},
    )
    def get(self, request):
        total_payments = Payment.objects.filter(status="COMPLETED").aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        total_comm = CommissionRecord.objects.filter(is_settled=True).aggregate(total=Sum("commission_amount"))["total"] or Decimal("0.00")
        total_escrow = EscrowHold.objects.filter(status=EscrowStatus.HELD).aggregate(total=Sum("held_amount"))["total"] or Decimal("0.00")
        total_payouts = ProfessionalPayout.objects.filter(status="COMPLETED").aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        total_refunds = RefundRequest.objects.filter(status="COMPLETED").aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        pending_refunds = RefundRequest.objects.filter(status="PENDING").count()
        pending_payouts = ProfessionalPayout.objects.filter(status="REQUESTED").count()

        data = {
            "total_platform_revenue": total_comm,
            "total_commission_earned": total_comm,
            "total_payments_collected": total_payments,
            "total_escrow_held": total_escrow,
            "total_payouts_completed": total_payouts,
            "total_refunds_processed": total_refunds,
            "pending_refunds_count": pending_refunds,
            "pending_payouts_count": pending_payouts,
        }
        return Response(data, status=status.HTTP_200_OK)


class AdminPaymentsListAPIView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(tags=["Admin - Financials"], summary="Global payment transactions log")
    def get_queryset(self):
        return Payment.objects.all().order_by("-created_at")


class AdminRefundsListAPIView(generics.ListAPIView):
    serializer_class = RefundRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(tags=["Admin - Financials"], summary="List customer refund requests")
    def get_queryset(self):
        return RefundRequest.objects.all().order_by("-created_at")


class AdminRefundActionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["Admin - Financials"],
        summary="Approve or reject a refund request",
        request=AdminRefundActionSerializer,
        responses={200: RefundRequestSerializer},
    )
    def post(self, request, pk):
        refund_req = RefundRequest.objects.get(id=pk)
        serializer = AdminRefundActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        updated = RefundService.process_refund_action(
            refund_request=refund_req,
            action=data["action"],
            admin_user=request.user,
            admin_notes=data.get("admin_notes", ""),
        )
        return Response(RefundRequestSerializer(updated).data, status=status.HTTP_200_OK)


class AdminPayoutsListAPIView(generics.ListAPIView):
    serializer_class = ProfessionalPayoutSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(tags=["Admin - Financials"], summary="List professional withdrawal payout requests")
    def get_queryset(self):
        return ProfessionalPayout.objects.all().order_by("-created_at")


class AdminPayoutActionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["Admin - Financials"],
        summary="Process (complete or fail) a payout request",
        request=AdminPayoutActionSerializer,
        responses={200: ProfessionalPayoutSerializer},
    )
    def post(self, request, pk):
        payout = ProfessionalPayout.objects.get(id=pk)
        serializer = AdminPayoutActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        updated = PayoutService.process_payout_action(
            payout=payout,
            action=data["action"],
            admin_user=request.user,
            admin_notes=data.get("admin_notes", ""),
            failure_reason=data.get("failure_reason", ""),
        )
        return Response(ProfessionalPayoutSerializer(updated).data, status=status.HTTP_200_OK)


class AdminPromoCodesListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = AdminPromoCodeSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(tags=["Admin - Financials"], summary="List or create promo discount codes")
    def get_queryset(self):
        return PromoCode.objects.all().order_by("-created_at")
