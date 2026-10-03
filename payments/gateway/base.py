from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict


class AbstractPaymentGateway(ABC):
    @abstractmethod
    def create_order(self, amount: Decimal, currency: str, reference: str, customer_info: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a remote order/session with the payment provider."""
        pass

    @abstractmethod
    def verify_payment(self, gateway_transaction_id: str, order_id: str, amount: Decimal) -> bool:
        """Verifies payment signature / callback confirmation from provider."""
        pass

    @abstractmethod
    def refund_payment(self, gateway_transaction_id: str, amount: Decimal, reason: str) -> Dict[str, Any]:
        """Initiates refund via gateway provider."""
        pass
