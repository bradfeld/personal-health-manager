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

@register.filter
def pace(duration_td, distance):
    """
    Calculate pace as time per distance unit (e.g., min/mile or min/km)
    Args:
        duration_td: timedelta object representing duration
        distance: float representing distance in miles or km
    Returns:
        String representation of pace in format "X:XX /mi" or "X:XX /km"
    """
    try:
        if not isinstance(duration_td, timedelta) or not distance or float(distance) <= 0:
            return "—"
        
        # Calculate seconds per distance unit
        total_seconds = duration_td.total_seconds()
        seconds_per_unit = total_seconds / float(distance)
        
        # Convert to minutes and seconds
        minutes = int(seconds_per_unit // 60)
        seconds = int(seconds_per_unit % 60)
        
        # Format as MM:SS
        return f"{minutes}:{seconds:02d}"
    except (ValueError, TypeError, ZeroDivisionError):
        return "—" 