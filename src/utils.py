"""
Utility functions for the Elasticsearch Alert Notificator.
"""

import logging
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


def calculate_downtime(alert_start: str, alert_end: str) -> str:
    """
    Calculate the downtime between alert_start and alert_end.
    
    Args:
        alert_start: ISO format datetime string for when the alert started
        alert_end: ISO format datetime string for when the alert ended
        
    Returns:
        str: Human-readable downtime duration
        
    Raises:
        Exception: If parsing fails or dates are invalid
    """
    start = date_parser.parse(alert_start)
    end = date_parser.parse(alert_end)
    delta = end - start
    
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        return "Invalid duration"
    
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    
    return " ".join(parts)
