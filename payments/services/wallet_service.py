from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from payments.models import Wallet, WalletTransaction, TransactionType


class WalletService:
    @staticmethod
    def get_or_create_wallet(user) -> Wallet:
        wallet, _ = Wallet.objects.get_or_create(
            user=user,
            defaults={"current_balance": Decimal("0.00"), "pending_balance": Decimal("0.00")}
        )
        return wallet

    @staticmethod
    def credit_wallet(
        user,
        amount: Decimal,
        transaction_type: str,
        reference_id: str,
        description: str,
    ) -> WalletTransaction:
        if amount <= Decimal("0.00"):
            raise ValidationError("Credit amount must be greater than zero.")

        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=user)
            if wallet.is_frozen:
                raise ValidationError("Wallet is frozen by administration.")

            wallet.current_balance += amount
            wallet.save(update_fields=["current_balance", "updated_at"])

            txn = WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type=transaction_type,
                amount=amount,
                balance_after=wallet.current_balance,
                reference_id=reference_id,
                description=description,
            )
            return txn

    @staticmethod
    def debit_wallet(
        user,
        amount: Decimal,
        transaction_type: str,
        reference_id: str,
        description: str,
    ) -> WalletTransaction:
        if amount <= Decimal("0.00"):
            raise ValidationError("Debit amount must be greater than zero.")

        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=user)
            if wallet.is_frozen:
                raise ValidationError("Wallet is frozen by administration.")

            if wallet.current_balance < amount:
                raise ValidationError(
                    f"Insufficient wallet balance. Required: ₹{amount}, Available: ₹{wallet.current_balance}"
                )

            wallet.current_balance -= amount
            wallet.save(update_fields=["current_balance", "updated_at"])

            txn = WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type=transaction_type,
                amount=amount,
                balance_after=wallet.current_balance,
                reference_id=reference_id,
                description=description,
            )
            return txn

    @staticmethod
    def add_pending_balance(user, amount: Decimal) -> None:
        if amount <= Decimal("0.00"):
            return
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=user)
            wallet.pending_balance += amount
            wallet.save(update_fields=["pending_balance", "updated_at"])

    @staticmethod
    def remove_pending_balance(user, amount: Decimal) -> None:
        if amount <= Decimal("0.00"):
            return
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=user)
            wallet.pending_balance = max(Decimal("0.00"), wallet.pending_balance - amount)
            wallet.save(update_fields=["pending_balance", "updated_at"])
