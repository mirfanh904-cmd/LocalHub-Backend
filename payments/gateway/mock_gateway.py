import uuid
from decimal import Decimal
from typing import Any, Dict
from .base import AbstractPaymentGateway


class MockPaymentGateway(AbstractPaymentGateway):
    """
    Deterministic mock gateway for development, staging, and automated testing.
    Emulates realistic gateway behavior (order generation, verification, and refunds).
    """

    def create_order(self, amount: Decimal, currency: str, reference: str, customer_info: Dict[str, Any]) -> Dict[str, Any]:
        order_id = f"order_mock_{uuid.uuid4().hex[:12]}"
        return {
            "gateway": "MockPaymentGateway",
            "order_id": order_id,
            "reference": reference,
            "amount": str(amount),
            "currency": currency,
            "status": "created",
            "mock_client_secret": f"sec_mock_{uuid.uuid4().hex[:16]}",
        }

    def verify_payment(self, gateway_transaction_id: str, order_id: str, amount: Decimal) -> bool:
        # Fails only if transaction id starts with 'mock_fail'
        if gateway_transaction_id.startswith("mock_fail"):
            return False
        return True

    def refund_payment(self, gateway_transaction_id: str, amount: Decimal, reason: str) -> Dict[str, Any]:
        refund_id = f"rfnd_mock_{uuid.uuid4().hex[:12]}"
        return {
            "gateway": "MockPaymentGateway",
            "refund_id": refund_id,
            "gateway_transaction_id": gateway_transaction_id,
            "amount": str(amount),
            "status": "processed",
            "reason": reason,
        }
