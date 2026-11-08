from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def sum(iterable, attr=None):
    total = Decimal('0')
    for item in iterable or []:
        value = getattr(item, attr) if attr else item
        if value is None:
            continue
        try:
            total += Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            continue
    return total
