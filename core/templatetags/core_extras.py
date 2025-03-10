from django import template
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
import pytz

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
        distance: float representing distance in miles or km (already converted to display units)
    Returns:
        String representation of pace in format "X:XX" (minutes:seconds per distance unit)
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

@register.simple_tag
def calculate_pace(duration_td, distance, conversion_factor):
    """
    Calculate pace with unit conversion
    Args:
        duration_td: timedelta object representing duration
        distance: float representing raw distance
        conversion_factor: float representing the multiplier to convert to display units
    Returns:
        String representation of pace in format "X:XX" (minutes:seconds per distance unit)
    """
    try:
        # Convert distance to display units
        distance_converted = float(distance) * float(conversion_factor)
        
        if not isinstance(duration_td, timedelta) or distance_converted <= 0:
            return "—"
        
        # Calculate seconds per distance unit
        total_seconds = duration_td.total_seconds()
        seconds_per_unit = total_seconds / distance_converted
        
        # Convert to minutes and seconds
        minutes = int(seconds_per_unit // 60)
        seconds = int(seconds_per_unit % 60)
        
        # Format as MM:SS
        return f"{minutes}:{seconds:02d}"
    except (ValueError, TypeError, ZeroDivisionError):
        return "—"

@register.filter
def localize_datetime(dt):
    """
    Convert a datetime to an ISO format string for client-side formatting
    Args:
        dt: datetime object
    Returns:
        ISO formatted datetime string with UTC timezone
    """
    if dt is None:
        return ""
    
    # If the datetime is naive (no timezone info), assume it's UTC
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    
    # Return ISO format for JavaScript to handle
    return dt.isoformat() 