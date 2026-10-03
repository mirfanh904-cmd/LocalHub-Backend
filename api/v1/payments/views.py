from decimal import Decimal
from django.db.models import Sum
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter

from payments.models import (
    Wallet,
    WalletTransaction,
    PromoCode,
    Payment,
    CommissionRecord,
    ProfessionalPayout,
    RefundRequest,
    Invoice,
    TransactionType,
)
from payments.services import (
    WalletService,
    PaymentService,
    RefundService,
    PayoutService,
)
from api.permissions import IsCustomer, IsProfessional, IsAdmin
from .serializers import (
    WalletSerializer,
    WalletTransactionSerializer,
    WalletTopupSerializer,
    PromoCodeValidateSerializer,
    PromoCodeResponseSerializer,
    CheckoutRequestSerializer,
    PaymentSerializer,
    InvoiceSerializer,
    RefundRequestCreateSerializer,
    RefundRequestSerializer,
    ProfessionalEarningsSerializer,
    PayoutRequestCreateSerializer,
    ProfessionalPayoutSerializer,
)


class WalletDetailView(generics.RetrieveAPIView):
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=["Payments - Wallet"], summary="Get current user wallet & balance")
    def get_object(self):
        return WalletService.get_or_create_wallet(self.request.user)


class WalletTransactionsListView(generics.ListAPIView):
    serializer_class = WalletTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=["Payments - Wallet"], summary="List wallet ledger transactions")
    def get_queryset(self):
        wallet = WalletService.get_or_create_wallet(self.request.user)
        return wallet.transactions.all().order_by("-created_at")


class WalletTopupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Payments - Wallet"],
        summary="Simulate wallet balance topup (Dev / Customer)",
        request=WalletTopupSerializer,
        responses={200: WalletSerializer},
    )
    def post(self, request):
        serializer = WalletTopupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]

        txn = WalletService.credit_wallet(
            user=request.user,
            amount=amount,
            transaction_type=TransactionType.WALLET_TOPUP,
            reference_id=f"TOPUP-{request.user.id.hex[:6].upper()}",
            description="Wallet Balance Top-up",
        )
        wallet = WalletService.get_or_create_wallet(request.user)
        return Response(WalletSerializer(wallet).data, status=status.HTTP_200_OK)


class PromoCodeValidateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Payments - Promo"],
        summary="Validate promo code & preview discount",
        request=PromoCodeValidateSerializer,
        responses={200: PromoCodeResponseSerializer},
    )
    def post(self, request):
        serializer = PromoCodeValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]
        subtotal = serializer.validated_data["subtotal"]

        promo = PromoCode.objects.filter(code__iexact=code.strip()).first()
        if not promo:
            return Response({"detail": "Promo code not found."}, status=status.HTTP_404_NOT_FOUND)

        is_valid, msg = promo.is_valid(subtotal)
        if not is_valid:
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

        discount = promo.calculate_discount(subtotal)
        final_amount = max(Decimal("0.00"), subtotal - discount)

        resp_data = {
            "id": promo.id,
            "code": promo.code,
            "description": promo.description,
            "discount_type": promo.discount_type,
            "discount_value": promo.discount_value,
            "discount_amount": discount,
            "final_amount": final_amount,
            "min_order_amount": promo.min_order_amount,
        }
        return Response(resp_data, status=status.HTTP_200_OK)


class CheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Payments - Checkout"],
        summary="Process booking or task payment checkout (Idempotent)",
        request=CheckoutRequestSerializer,
        responses={201: PaymentSerializer},
    )
    def post(self, request):
        serializer = CheckoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        payment = PaymentService.process_checkout(
            customer=request.user,
            target_type=data["target_type"],
            target_id=data["target_id"],
            payment_method=data["payment_method"],
            idempotency_key=data["idempotency_key"],
            promo_code_str=data.get("promo_code"),
            gateway_txn_id=data.get("gateway_transaction_id"),
        )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class CustomerInvoicesListView(generics.ListAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=["Payments - Invoices"], summary="List customer invoices")
    def get_queryset(self):
        return Invoice.objects.filter(customer=self.request.user).order_by("-issued_at")


class InvoiceDetailView(generics.RetrieveAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    @extend_schema(tags=["Payments - Invoices"], summary="Get invoice detail")
    def get_queryset(self):
        if getattr(self.request.user, "role", None) == "ADMIN" or self.request.user.is_superuser:
            return Invoice.objects.all()
        return Invoice.objects.filter(customer=self.request.user)


class CustomerRefundsListView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return RefundRequestCreateSerializer
        return RefundRequestSerializer

    @extend_schema(tags=["Payments - Refunds"], summary="List or create customer refund requests")
    def get_queryset(self):
        return RefundRequest.objects.filter(customer=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        data = serializer.validated_data
        refund = RefundService.request_refund(
            customer=self.request.user,
            payment_id=data["payment_id"],
            amount=data["amount"],
            reason=data["reason"],
            refund_method=data.get("refund_method", "WALLET_CREDIT"),
        )
        return refund

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refund = self.perform_create(serializer)
        return Response(RefundRequestSerializer(refund).data, status=status.HTTP_201_CREATED)


class ProfessionalEarningsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProfessional]

    @extend_schema(
        tags=["Payments - Professional"],
        summary="Get professional net earnings and breakdown",
        responses={200: ProfessionalEarningsSerializer},
    )
    def get(self, request):
        user = request.user
        wallet = WalletService.get_or_create_wallet(user)

        comm_records = CommissionRecord.objects.filter(professional=user).order_by("-created_at")
        gross = comm_records.aggregate(total=Sum("gross_amount"))["total"] or Decimal("0.00")
        comm = comm_records.aggregate(total=Sum("commission_amount"))["total"] or Decimal("0.00")
        net = comm_records.aggregate(total=Sum("net_earning"))["total"] or Decimal("0.00")

        payouts = ProfessionalPayout.objects.filter(professional=user, status="COMPLETED")
        withdrawn = payouts.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        breakdown = [
            {
                "id": str(r.id),
                "reference": r.payment.payment_reference,
                "gross_amount": str(r.gross_amount),
                "commission_amount": str(r.commission_amount),
                "net_earning": str(r.net_earning),
                "service_title": getattr(r.booking.service, "name", getattr(r.booking.service, "title", "Service")) if r.booking else (r.task.title if r.task else "Service"),
                "date": r.created_at.strftime("%Y-%m-%d %H:%M"),
                "is_settled": r.is_settled,
            }
            for r in comm_records[:20]
        ]

        data = {
            "current_balance": wallet.current_balance,
            "pending_escrow": wallet.pending_balance,
            "total_gross_earnings": gross,
            "total_commission_paid": comm,
            "total_net_earnings": net,
            "total_withdrawn": withdrawn,
            "earnings_breakdown": breakdown,
        }
        return Response(data, status=status.HTTP_200_OK)


class ProfessionalPayoutsListView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsProfessional]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PayoutRequestCreateSerializer
        return ProfessionalPayoutSerializer

    @extend_schema(tags=["Payments - Professional"], summary="List or request payouts for professional")
    def get_queryset(self):
        return ProfessionalPayout.objects.filter(professional=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        data = serializer.validated_data
        payout = PayoutService.request_payout(
            professional=self.request.user,
            amount=data["amount"],
            payout_method=data.get("payout_method", "UPI"),
            account_details=data.get("account_details", {}),
        )
        return payout

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payout = self.perform_create(serializer)
        return Response(ProfessionalPayoutSerializer(payout).data, status=status.HTTP_201_CREATED)
