"""Creates the PlatformSettings row and backfills the money split on order lines placed before
commissions existed (at the default rate), plus `PaymentRecord.amount` from each order's lines."""

from decimal import ROUND_HALF_UP, Decimal

from django.db import migrations

DEFAULT_RATE = Decimal("10.00")
CENT = Decimal("0.01")


def backfill(apps, schema_editor):
    PlatformSettings = apps.get_model("finance", "PlatformSettings")
    OrderItem = apps.get_model("orders", "OrderItem")
    PaymentRecord = apps.get_model("payments", "PaymentRecord")

    PlatformSettings.objects.get_or_create(pk=1, defaults={"default_commission_rate": DEFAULT_RATE})

    for item in OrderItem.objects.filter(commission_rate=0, commission_amount=0, vendor_earning=0):
        subtotal = item.unit_price * item.quantity
        commission = (subtotal * DEFAULT_RATE / 100).quantize(CENT, rounding=ROUND_HALF_UP)
        item.commission_rate = DEFAULT_RATE
        item.commission_amount = commission
        item.vendor_earning = subtotal - commission
        item.save(update_fields=["commission_rate", "commission_amount", "vendor_earning"])

    for payment in PaymentRecord.objects.filter(amount=0):
        payment.amount = sum(
            (i.unit_price * i.quantity for i in OrderItem.objects.filter(order_id=payment.order_id)),
            Decimal("0.00"),
        )
        payment.save(update_fields=["amount"])


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0001_initial"),
        ("orders", "0004_orderitem_commission_amount_and_more"),
        ("payments", "0002_paymentrecord_amount"),
    ]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
