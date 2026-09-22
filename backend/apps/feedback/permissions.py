"""Purchase-verification gate for Reviews (FR-001/FR-002). Re-checked live against `OrderItem`
on every write, never cached on the Review row or trusted from a client-supplied flag
(research.md §2, Constitution Principle I).
"""

from apps.orders.models import OrderItem


def has_delivered_purchase(customer, product):
    return OrderItem.objects.filter(
        order__customer=customer, product=product, status=OrderItem.Status.DELIVERED
    ).exists()
