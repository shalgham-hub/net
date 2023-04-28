from django import template
from ..utils import prettify_bytes as _prettify_bytes

register = template.Library()


@register.filter
def prettify_bytes(num, suffix='B'):
    return _prettify_bytes(num=num, suffix=suffix)
