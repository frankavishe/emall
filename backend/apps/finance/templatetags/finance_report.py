from decimal import Decimal, InvalidOperation

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from apps.vendors.models import Shop

register = template.Library()


@register.filter
def money(value):
    """`TZS 12,500`, whole shillings like the app's `formatCurrency`."""

    try:
        amount = Decimal(value or 0)
    except InvalidOperation:
        return value
    return f"TZS {amount:,.0f}"


@register.filter
def rate(value):
    """A commission percentage without trailing zeros, e.g. `12.5%`."""

    if value is None:
        return ""
    return f"{Decimal(value).normalize():f}%"


@register.filter
def network(value):
    """A mobile-money network's display name, e.g. `MPESA` -> `M-Pesa`."""

    return dict(Shop.PayoutNetwork.choices).get(value, value)


@register.filter
def breakable(value, size=18):
    """Long unbroken text (payment references) split into `size`-character lines, since the PDF
    renderer won't wrap inside a word and it would spill into the next column."""

    text = str(value or "")
    return mark_safe("<br>".join(escape(text[i : i + size]) for i in range(0, len(text), size)))
