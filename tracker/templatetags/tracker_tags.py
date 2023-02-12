from typing import Any

from django import template

register = template.Library()


@register.simple_tag
def setvar(val: Any) -> Any:
    return val
