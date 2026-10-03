from decimal import Decimal
from typing import Optional
from payments.models import CommissionRecord, Payment


class CommissionService:
    DEFAULT_COMMISSION_PERCENTAGE = Decimal("10.00")

    @classmethod
    def calculate_commission(cls, gross_amount: Decimal, rate_percentage: Optional[Decimal] = None) -> tuple[Decimal, Decimal]:
        rate = rate_percentage if rate_percentage is not None else cls.DEFAULT_COMMISSION_PERCENTAGE
        commission = (gross_amount * rate / Decimal("100.00")).quantize(Decimal("0.01"))
        net_earning = gross_amount - commission
        return commission, net_earning

    @classmethod
    def create_commission_record(
        cls,
        payment: Payment,
        professional,
        booking=None,
        task=None,
        rate_percentage: Optional[Decimal] = None,
    ) -> CommissionRecord:
        rate = rate_percentage if rate_percentage is not None else cls.DEFAULT_COMMISSION_PERCENTAGE
        gross = payment.total_amount
        commission, net = cls.calculate_commission(gross, rate)

        record = CommissionRecord.objects.create(
            payment=payment,
            booking=booking,
            task=task,
            professional=professional,
            gross_amount=gross,
            commission_rate_percentage=rate,
            commission_amount=commission,
            net_earning=net,
            is_settled=False,
        )
        return record
