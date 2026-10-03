import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from common.models import BaseModel


class TransactionType(models.TextChoices):
    WALLET_TOPUP = "WALLET_TOPUP", "Wallet Top-up"
    WALLET_DEBIT = "WALLET_DEBIT", "Wallet Debit (Payment)"
    EARNING_CREDIT = "EARNING_CREDIT", "Professional Earning Credit"
    REFUND_CREDIT = "REFUND_CREDIT", "Refund Credit"
    PAYOUT_DEBIT = "PAYOUT_DEBIT", "Payout Withdrawal Debit"
    ADJUSTMENT = "ADJUSTMENT", "Administrative Adjustment"


class Wallet(BaseModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet",
    )
    current_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Available funds for checkout or payout.",
    )
    pending_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Funds locked in active escrow or pending payout.",
    )
    currency = models.CharField(
        max_length=10,
        default="INR",
    )
    is_frozen = models.BooleanField(
        default=False,
        help_text="Admin lock to prevent balance transactions.",
    )

    class Meta:
        db_table = "payments_wallet"
        verbose_name = "User Wallet"
        verbose_name_plural = "User Wallets"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(current_balance__gte=Decimal("0.00")),
                name="wallet_current_balance_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(pending_balance__gte=Decimal("0.00")),
                name="wallet_pending_balance_non_negative",
            ),
        ]

    def __str__(self):
        return f"Wallet ({self.user.email}) - Balance: ₹{self.current_balance}"


class WalletTransaction(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    transaction_type = models.CharField(
        max_length=30,
        choices=TransactionType.choices,
        db_index=True,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Transaction monetary amount.",
    )
    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Snapshot of available balance immediately after transaction.",
    )
    reference_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Associated Payment, Refund, Payout, or System reference ID.",
    )
    description = models.CharField(
        max_length=255,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        db_table = "payments_wallet_transaction"
        ordering = ["-created_at"]
        verbose_name = "Wallet Ledger Transaction"
        verbose_name_plural = "Wallet Ledger Transactions"

    def __str__(self):
        return f"{self.transaction_type} (₹{self.amount}) - Ref: {self.reference_id}"
