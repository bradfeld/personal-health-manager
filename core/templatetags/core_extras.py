from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def duration(td):
    if not isinstance(td, timedelta):
        return td
    
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    if hours > 0:
        return f'{hours}h {minutes}m'
    else:
        return f'{minutes}m' 

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value 