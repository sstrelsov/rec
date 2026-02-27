#!/usr/bin/env python3
"""
traffic_analyzer.py - Real-time traffic logging

Prints a compact one-line-per-request log during capture.
Filters out ads/analytics traffic.
"""

import time
import sys
import os
from mitmproxy import http, ctx

# Add parent directory to path to find config module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from domain_utils import matches_target_domains, is_blocked_traffic


class TrafficAnalyzer:
    """Real-time one-line-per-request logging addon."""

    def load(self, loader):
        """Configure addon options."""
        loader.add_option(
            "traffic_analyzer_enabled", bool, True,
            "Enable real-time traffic logging"
        )

    def request(self, flow: http.HTTPFlow):
        """Track request start time."""
        if not ctx.options.traffic_analyzer_enabled:
            return

        if not matches_target_domains(flow.request.pretty_host, config.target_domains):
            return

        if is_blocked_traffic(flow, config.blocked_patterns):
            return

        flow.request.analyzer_start_time = time.time()

    def response(self, flow: http.HTTPFlow):
        """Print one-line log for each completed response."""
        if not ctx.options.traffic_analyzer_enabled:
            return

        if not matches_target_domains(flow.request.pretty_host, config.target_domains):
            return

        if is_blocked_traffic(flow, config.blocked_patterns):
            return

        # Calculate response time
        start_time = getattr(flow.request, 'analyzer_start_time', None)
        if start_time:
            elapsed_ms = (time.time() - start_time) * 1000
        else:
            elapsed_ms = 0

        status = flow.response.status_code if flow.response else 0
        method = flow.request.method
        host = flow.request.pretty_host
        path = flow.request.path

        # Truncate path if too long
        url = f"{host}{path}"
        if len(url) > 80:
            url = url[:77] + "..."

        print(f"{method:<6} {status:<3}  {elapsed_ms:>6.0f}ms  {url}")


# Register the addon
addons = [TrafficAnalyzer()]
