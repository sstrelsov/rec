#!/usr/bin/env python3
"""
context_detector.py - Request Context Detection Utility

Detects whether requests are:
- Browser requests (user browsing, loading web pages)
- Frontend-Backend API communication (apps communicating with servers)

This information is used across all addons and outputs for better filtering and analysis.
"""

import re
from enum import Enum
from typing import Dict, Any, Optional
from mitmproxy import http


class RequestContext(Enum):
    """Request context types."""
    BROWSER = "browser"           # User browsing, loading web pages
    FRONTEND_BACKEND = "api"      # App-to-app/frontend-to-backend communication
    UNKNOWN = "unknown"           # Cannot determine


def detect_request_context(flow: http.HTTPFlow) -> RequestContext:
    """
    Detect request context from HTTP flow.

    Args:
        flow: mitmproxy HTTPFlow object

    Returns:
        RequestContext enum indicating the type of request
    """
    if not flow or not flow.request:
        return RequestContext.UNKNOWN

    # Analyze various indicators
    browser_score = 0
    api_score = 0

    # 1. User-Agent Analysis
    user_agent = flow.request.headers.get('user-agent', '').lower()
    if user_agent:
        browser_score += _analyze_user_agent(user_agent)
        api_score += _analyze_api_user_agent(user_agent)

    # 2. Request Headers Analysis
    browser_score += _analyze_browser_headers(flow.request.headers)
    api_score += _analyze_api_headers(flow.request.headers)

    # 3. Content Type Analysis
    if flow.response:
        browser_score += _analyze_browser_response(flow.response)
        api_score += _analyze_api_response(flow.response)

    # 4. URL Path Analysis
    browser_score += _analyze_browser_path(flow.request.path)
    api_score += _analyze_api_path(flow.request.path)

    # 5. Request Method Analysis
    browser_score += _analyze_browser_method(flow.request.method)
    api_score += _analyze_api_method(flow.request.method)

    # 6. Request Body Analysis
    if flow.request.content:
        browser_score += _analyze_browser_body(flow.request)
        api_score += _analyze_api_body(flow.request)

    # Determine context based on scores
    if api_score > browser_score and api_score >= 3:
        return RequestContext.FRONTEND_BACKEND
    elif browser_score > api_score and browser_score >= 2:
        return RequestContext.BROWSER
    else:
        return RequestContext.UNKNOWN


def _analyze_user_agent(user_agent: str) -> int:
    """Analyze User-Agent for browser patterns. Returns browser score (0-3)."""
    score = 0

    # Strong browser indicators
    browser_patterns = [
        r'mozilla/.*gecko', r'webkit', r'chrome/', r'safari/', r'firefox/',
        r'edge/', r'opera/', r'chromium/', r'mobile safari'
    ]

    for pattern in browser_patterns:
        if re.search(pattern, user_agent):
            score += 2
            break

    # Browser-specific features
    browser_features = ['applewebkit', 'gecko', 'khtml', 'trident']
    for feature in browser_features:
        if feature in user_agent:
            score += 1
            break

    return min(score, 3)


def _analyze_api_user_agent(user_agent: str) -> int:
    """Analyze User-Agent for API client patterns. Returns API score (0-3)."""
    score = 0

    # Strong API client indicators
    api_patterns = [
        r'okhttp', r'axios', r'fetch', r'curl', r'python-requests',
        r'java/', r'node\.js', r'go-http-client', r'apache-httpclient',
        r'restsharp', r'alamofire', r'retrofit', r'volley'
    ]

    for pattern in api_patterns:
        if re.search(pattern, user_agent):
            score += 3
            break

    # Generic programming language/framework indicators
    generic_api = [
        'python', 'java', 'kotlin', 'swift', 'javascript', 'node',
        'react', 'angular', 'vue', 'flutter', 'dart'
    ]

    for indicator in generic_api:
        if indicator in user_agent:
            score += 1
            break

    return min(score, 3)


def _analyze_browser_headers(headers) -> int:
    """Analyze headers for browser patterns. Returns browser score (0-3)."""
    score = 0

    # Browser-typical headers
    if 'accept' in headers:
        accept = headers['accept'].lower()
        if 'text/html' in accept and 'application/xhtml' in accept:
            score += 2
        elif 'text/html' in accept:
            score += 1

    # Browser navigation headers
    if 'referer' in headers or 'referrer' in headers:
        score += 1

    # Browser-specific headers
    browser_headers = [
        'accept-language', 'accept-encoding', 'cache-control',
        'upgrade-insecure-requests', 'dnt', 'sec-fetch-site',
        'sec-fetch-mode', 'sec-fetch-dest'
    ]

    browser_header_count = sum(1 for h in browser_headers if h in headers)
    if browser_header_count >= 4:
        score += 2
    elif browser_header_count >= 2:
        score += 1

    return min(score, 3)


def _analyze_api_headers(headers) -> int:
    """Analyze headers for API patterns. Returns API score (0-3)."""
    score = 0

    # API-specific headers
    api_headers = [
        'authorization', 'x-api-key', 'x-auth-token', 'bearer',
        'x-requested-with', 'x-csrf-token', 'x-custom-header'
    ]

    for header_name in headers:
        header_lower = header_name.lower()
        if any(api_header in header_lower for api_header in api_headers):
            score += 2
            break

    # Content-Type for APIs
    if 'content-type' in headers:
        content_type = headers['content-type'].lower()
        if 'application/json' in content_type:
            score += 2
        elif 'application/xml' in content_type or 'text/xml' in content_type:
            score += 1

    # Accept header preferring JSON/XML
    if 'accept' in headers:
        accept = headers['accept'].lower()
        if 'application/json' in accept and 'text/html' not in accept:
            score += 1
        elif 'application/xml' in accept:
            score += 1

    return min(score, 3)


def _analyze_browser_response(response) -> int:
    """Analyze response for browser patterns. Returns browser score (0-2)."""
    score = 0

    if not response:
        return 0

    # HTML responses are typically for browsers
    if 'content-type' in response.headers:
        content_type = response.headers['content-type'].lower()
        if 'text/html' in content_type:
            score += 2
        elif any(t in content_type for t in ['text/css', 'text/javascript', 'image/']):
            score += 1

    return min(score, 2)


def _analyze_api_response(response) -> int:
    """Analyze response for API patterns. Returns API score (0-2)."""
    score = 0

    if not response:
        return 0

    # JSON/XML responses are typically APIs
    if 'content-type' in response.headers:
        content_type = response.headers['content-type'].lower()
        if 'application/json' in content_type:
            score += 2
        elif any(t in content_type for t in ['application/xml', 'text/xml', 'application/api']):
            score += 1

    return min(score, 2)


def _analyze_browser_path(path: str) -> int:
    """Analyze URL path for browser patterns. Returns browser score (0-2)."""
    score = 0
    path_lower = path.lower()

    # Static web assets
    static_extensions = ['.html', '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.woff']
    if any(path_lower.endswith(ext) for ext in static_extensions):
        score += 2

    # Root or common web paths
    if path in ['/', '/index', '/home', '/login', '/register']:
        score += 1

    return min(score, 2)


def _analyze_api_path(path: str) -> int:
    """Analyze URL path for API patterns. Returns API score (0-2)."""
    score = 0
    path_lower = path.lower()

    # Strong API indicators
    api_patterns = ['/api/', '/v1/', '/v2/', '/v3/', '/rest/', '/graphql', '/rpc/']
    if any(pattern in path_lower for pattern in api_patterns):
        score += 2

    # Common API endpoints
    elif any(endpoint in path_lower for endpoint in ['/users', '/auth', '/data', '/service']):
        score += 1

    return min(score, 2)


def _analyze_browser_method(method: str) -> int:
    """Analyze HTTP method for browser patterns. Returns browser score (0-1)."""
    # Browsers primarily use GET and POST
    if method.upper() == 'GET':
        return 1
    return 0


def _analyze_api_method(method: str) -> int:
    """Analyze HTTP method for API patterns. Returns API score (0-1)."""
    # APIs commonly use PUT, DELETE, PATCH
    api_methods = ['PUT', 'DELETE', 'PATCH']
    if method.upper() in api_methods:
        return 1
    return 0


def _analyze_browser_body(request) -> int:
    """Analyze request body for browser patterns. Returns browser score (0-1)."""
    if not request.content:
        return 0

    content_type = request.headers.get('content-type', '').lower()

    # Form data is typical for browsers
    if 'application/x-www-form-urlencoded' in content_type:
        return 1
    elif 'multipart/form-data' in content_type:
        return 1

    return 0


def _analyze_api_body(request) -> int:
    """Analyze request body for API patterns. Returns API score (0-1)."""
    if not request.content:
        return 0

    content_type = request.headers.get('content-type', '').lower()

    # JSON is typical for APIs
    if 'application/json' in content_type:
        return 1
    elif 'application/xml' in content_type or 'text/xml' in content_type:
        return 1

    return 0


def get_context_info(context: RequestContext) -> Dict[str, Any]:
    """Get human-readable information about a request context."""
    context_info = {
        RequestContext.BROWSER: {
            "name": "Browser",
            "description": "User browsing web pages, loading static assets",
            "icon": "🌐",
            "color": "#3b82f6"  # Blue
        },
        RequestContext.FRONTEND_BACKEND: {
            "name": "API",
            "description": "Frontend-backend or app-to-app communication",
            "icon": "⚡",
            "color": "#10b981"  # Green
        },
        RequestContext.UNKNOWN: {
            "name": "Unknown",
            "description": "Could not determine request context",
            "icon": "❓",
            "color": "#6b7280"  # Gray
        }
    }

    return context_info.get(context, context_info[RequestContext.UNKNOWN])
