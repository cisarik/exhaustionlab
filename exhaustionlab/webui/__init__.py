"""
Web UI package for ExhaustionLab.

Provides FastAPI-powered endpoints plus HTML/CSS/JS assets
for the debugging console, evolution visualization, and
strategy hall-of-fame dashboard.
"""

from .server import create_app

__all__ = ["create_app"]
