"""Channel-layer group names: who hears about what.

- `order.<id>`: whoever is watching that one order (a guest holding its token, or its customer).
- `user.<id>`: one signed-in account's own sockets: a customer's orders, a vendor's or rider's
  lines.
- `admins`: every signed-in Administrator.
"""

from apps.orders.models import Order, OrderItem

ADMINS = "admins"


def order_group(order_id):
    return f"order.{order_id}"


def user_group(user_id):
    return f"user.{user_id}"


def buyer_groups(order_id):
    """The order's own group, plus its customer's account (guests have none)."""

    customer_id = Order.objects.filter(pk=order_id).values_list("customer_id", flat=True).first()
    groups = [order_group(order_id)]
    if customer_id is not None:
        groups.append(user_group(customer_id))
    return groups


def vendor_groups(order_id):
    """One group per owner of a shop that sells something in the order."""

    owner_ids = (
        OrderItem.objects.filter(order_id=order_id)
        .values_list("product__shop__owner_id", flat=True)
        .distinct()
    )
    return [user_group(owner_id) for owner_id in owner_ids]


def rider_groups(order_id):
    rider_ids = (
        OrderItem.objects.filter(order_id=order_id, rider__isnull=False)
        .values_list("rider_id", flat=True)
        .distinct()
    )
    return [user_group(rider_id) for rider_id in rider_ids]


def order_audience(order_id):
    """Everyone who sees the order: its buyer, its vendors, its riders and the administrators."""

    return [*buyer_groups(order_id), ADMINS, *vendor_groups(order_id), *rider_groups(order_id)]
