#!/usr/bin/env python3
"""
traffic_analyzer.py - Real-time traffic analysis and statistics

Provides comprehensive traffic analysis including:
- Domain patterns and frequency
- Response time analysis
- Error rate monitoring
- Content type distribution
- Security issue detection

Filters out annoying ads/analytics traffic.
"""

import time
import json
import logging
from collections import defaultdict
from typing import Dict, List, Any, Optional
from mitmproxy import http, ctx
import sys
import os

# Add parent directory to path to find config module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from domain_utils import matches_target_domains
from addons.context_detector import detect_request_context, RequestContext, get_context_info


class TrafficAnalyzer:
    """Real-time traffic analysis and monitoring addon."""

    def __init__(self):
        self.flows_count = 0
        self.domain_stats = defaultdict(int)
        self.method_stats = defaultdict(int)
        self.status_stats = defaultdict(int)
        self.content_type_stats = defaultdict(int)
        self.context_stats = defaultdict(int)
        self.response_times = []

        # Performance tracking
        self.slow_requests = []
        self.large_responses = []
        self.error_patterns = defaultdict(list)

        # API pattern detection
        self.api_endpoints = defaultdict(lambda: {'methods': set(), 'count': 0, 'avg_time': 0})

    def load(self, loader):
        """Configure addon options."""
        loader.add_option(
            "traffic_analyzer_enabled", bool, True,
            "Enable real-time traffic analysis and reporting"
        )
        loader.add_option(
            "analyzer_alert_threshold", int, 5000,
            "Response time threshold (ms) for slow request alerts"
        )
        loader.add_option(
            "analyzer_size_threshold", int, 1048576,  # 1MB
            "Response size threshold (bytes) for large response alerts"
        )
        loader.add_option(
            "analyzer_report_interval", int, 50,
            "Print analysis report every N requests"
        )

    def request(self, flow: http.HTTPFlow):
        """Process incoming requests."""
        if not ctx.options.traffic_analyzer_enabled:
            return

        # Skip traffic not matching target domains
        if not matches_target_domains(flow.request.pretty_host, config.target_domains):
            return

        # Skip ads/analytics traffic
        if self._is_blocked_traffic(flow):
            return

        # Track request start time
        flow.request.analyzer_start_time = time.time()

        # Detect API patterns
        self._detect_api_patterns(flow)

    def response(self, flow: http.HTTPFlow):
        """Process completed responses."""
        if not ctx.options.traffic_analyzer_enabled:
            return

        # Skip traffic not matching target domains
        if not matches_target_domains(flow.request.pretty_host, config.target_domains):
            return

        # Skip ads/analytics traffic
        if self._is_blocked_traffic(flow):
            return

        self.flows_count += 1

        # Calculate response time
        start_time = getattr(flow.request, 'analyzer_start_time', None)
        if start_time:
            response_time = (time.time() - start_time) * 1000  # ms
            self.response_times.append(response_time)

            # Alert on slow requests
            if response_time > ctx.options.analyzer_alert_threshold:
                self.slow_requests.append({
                    'url': flow.request.pretty_url,
                    'time': response_time,
                    'method': flow.request.method
                })

        # Update statistics
        self._update_statistics(flow)

        # Check for large responses
        if flow.response and flow.response.content:
            size = len(flow.response.content)
            if size > ctx.options.analyzer_size_threshold:
                self.large_responses.append({
                    'url': flow.request.pretty_url,
                    'size': size,
                    'content_type': flow.response.headers.get('content-type', 'unknown')
                })

        # Print periodic reports
        if self.flows_count % ctx.options.analyzer_report_interval == 0:
            self._print_analysis_report()

    def _is_blocked_traffic(self, flow: http.HTTPFlow) -> bool:
        """Check if this traffic should be blocked (ads/analytics)."""
        url = flow.request.pretty_url.lower()
        host = flow.request.pretty_host.lower()
        path = flow.request.path.lower()

        # Check against blocked patterns
        for pattern in config.blocked_patterns:
            if pattern in url or pattern in host or pattern in path:
                return True

        # Check for tracking query parameters
        tracking_params = ['utm_', 'fbclid', 'gclid', '_ga', 'mc_', 'mkt_']
        for param in tracking_params:
            if param in url:
                return True

        return False

    def _detect_api_patterns(self, flow: http.HTTPFlow):
        """Detect and categorize API endpoints."""
        url = flow.request.pretty_url
        path = flow.request.path
        method = flow.request.method

        # Normalize API path for pattern detection
        normalized_path = self._normalize_api_path(path)

        # Update API endpoint statistics
        endpoint = self.api_endpoints[normalized_path]
        endpoint['methods'].add(method)
        endpoint['count'] += 1

    def _normalize_api_path(self, path: str) -> str:
        """Normalize API path by replacing IDs with placeholders."""
        import re

        # Replace common ID patterns
        patterns = [
            (r'/\d+', '/{id}'),  # Numeric IDs
            (r'/[a-f0-9-]{36}', '/{uuid}'),  # UUIDs
            (r'/[a-f0-9]{24}', '/{objectid}'),  # MongoDB ObjectIds
            (r'/[a-zA-Z0-9]{20,}', '/{token}')  # Long tokens/keys
        ]

        normalized = path
        for pattern, replacement in patterns:
            normalized = re.sub(pattern, replacement, normalized)

        return normalized

    def _update_statistics(self, flow: http.HTTPFlow):
        """Update traffic statistics."""
        # Domain stats
        domain = flow.request.pretty_host
        self.domain_stats[domain] += 1

        # Method stats
        self.method_stats[flow.request.method] += 1

        # Context stats
        context = detect_request_context(flow)
        self.context_stats[context.value] += 1

        # Status code stats
        if flow.response:
            self.status_stats[flow.response.status_code] += 1

            # Content type stats
            content_type = flow.response.headers.get('content-type', 'unknown')
            main_type = content_type.split(';')[0].strip()
            self.content_type_stats[main_type] += 1

            # Track error patterns
            if flow.response.status_code >= 400:
                self.error_patterns[flow.response.status_code].append(flow.request.pretty_url)

    def _print_analysis_report(self):
        """Print comprehensive analysis report."""
        logging.info("=" * 60)
        logging.info(f"📊 TRAFFIC ANALYSIS REPORT (Flows: {self.flows_count})")
        logging.info("=" * 60)

        # Top domains
        if self.domain_stats:
            logging.info("🌐 Top Domains:")
            for domain, count in sorted(self.domain_stats.items(), key=lambda x: x[1], reverse=True)[:5]:
                logging.info(f"  • {domain}: {count} requests")

        # Response time analysis
        if self.response_times:
            avg_time = sum(self.response_times) / len(self.response_times)
            max_time = max(self.response_times)
            logging.info(f"⏱️  Response Times: Avg {avg_time:.1f}ms, Max {max_time:.1f}ms")

        # Status code distribution
        if self.status_stats:
            logging.info("📊 Status Codes:")
            for status, count in sorted(self.status_stats.items()):
                logging.info(f"  • {status}: {count}")

        # Request context distribution
        if self.context_stats:
            logging.info("🎯 Request Context:")
            for context, count in sorted(self.context_stats.items()):
                icon = "🌐" if context == "browser" else "⚡" if context == "api" else "❓"
                logging.info(f"  • {icon} {context.title()}: {count}")

        # Performance alerts
        if self.slow_requests:
            recent_slow = self.slow_requests[-3:]  # Last 3 slow requests
            logging.info(f"🐌 Slow Requests (showing {len(recent_slow)} most recent):")
            for req in recent_slow:
                logging.info(f"  • {req['method']} {req['url']}: {req['time']:.1f}ms")

        # API endpoints
        if self.api_endpoints:
            popular_apis = sorted(self.api_endpoints.items(), key=lambda x: x[1]['count'], reverse=True)[:5]
            logging.info("🔗 Popular API Endpoints:")
            for path, stats in popular_apis:
                methods = ', '.join(sorted(stats['methods']))
                logging.info(f"  • {path} [{methods}]: {stats['count']} calls")

        logging.info("=" * 60)

    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get complete analysis summary for external use."""
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0

        return {
            'flows_processed': self.flows_count,
            'domains': dict(self.domain_stats),
            'methods': dict(self.method_stats),
            'status_codes': dict(self.status_stats),
            'content_types': dict(self.content_type_stats),
            'contexts': dict(self.context_stats),
            'avg_response_time_ms': avg_response_time,
            'slow_requests_count': len(self.slow_requests),
            'large_responses_count': len(self.large_responses),
            'api_endpoints_count': len(self.api_endpoints)
        }


# Register the addon
addons = [TrafficAnalyzer()]
