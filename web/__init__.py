"""
AEGIS Web Server Module
Provides Flask application, RESTful APIs, and static assets for the Command Center.
"""

from aegis.web.app import create_app

__all__ = ["create_app"]
