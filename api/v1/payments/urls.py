from django.urls import path
from .views import (
    WalletDetailView,
    WalletTransactionsListView,
    WalletTopupView,
    PromoCodeValidateView,
    CheckoutView,
    CustomerInvoicesListView,
    InvoiceDetailView,
    CustomerRefundsListView,
    ProfessionalEarningsView,
    ProfessionalPayoutsListView,
)

urlpatterns = [
    # Wallet & Top-up
    path("wallet/", WalletDetailView.as_view(), name="payment-wallet-detail"),
    path("wallet/transactions/", WalletTransactionsListView.as_view(), name="payment-wallet-transactions"),
    path("wallet/topup/", WalletTopupView.as_view(), name="payment-wallet-topup"),

    # Promo validation & Checkout
    path("promo/validate/", PromoCodeValidateView.as_view(), name="payment-promo-validate"),
    path("checkout/", CheckoutView.as_view(), name="payment-checkout"),

    # Invoices & Refunds
    path("invoices/", CustomerInvoicesListView.as_view(), name="payment-invoices-list"),
    path("invoices/<uuid:id>/", InvoiceDetailView.as_view(), name="payment-invoice-detail"),
    path("refunds/", CustomerRefundsListView.as_view(), name="payment-refunds-list"),

    # Professional Earnings & Payouts
    path("worker/earnings/", ProfessionalEarningsView.as_view(), name="payment-worker-earnings"),
    path("worker/payouts/", ProfessionalPayoutsListView.as_view(), name="payment-worker-payouts"),
]
