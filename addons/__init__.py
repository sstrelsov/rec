#!/usr/bin/env python3
"""
addons package - Enhanced mitmproxy addons for API analysis
"""

from .context_detector import detect_request_context, RequestContext

__all__ = ['detect_request_context', 'RequestContext']
