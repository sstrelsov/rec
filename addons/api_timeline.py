#!/usr/bin/env python3
"""
api_timeline.py - Chronological API Timeline Visualizer

Creates beautiful chronological visualizations of API calls, filtering out
annoying ads and analytics traffic to focus on the actual APIs you care about.
"""

import json
import time
import logging
from collections import defaultdict
from typing import Dict, List, Any, Set
from datetime import datetime
from pathlib import Path
from mitmproxy import http, ctx


class APITimeline:
    """Generate chronological timelines of API calls."""

    def __init__(self):
        self.api_calls = []
        self.domains_seen = set()

        # Comprehensive ads/analytics blocklist
        self.blocked_patterns = {
            # Analytics & Tracking
            'google-analytics.com', 'googleanalytics.com', 'google-analytics',
            'gtag', 'gtm.js', 'ga.js', '_ga', '/analytics/', '/tracking/',
            'mixpanel.com', 'amplitude.com', 'segment.com', 'segment.io',
            'hotjar.com', 'fullstory.com', 'logrocket.com', 'datadog',
            'newrelic.com', 'bugsnag.com', 'sentry.io', 'rollbar.com',

            # Advertising
            'googlesyndication.com', 'doubleclick.net', 'googleadservices.com',
            'facebook.com/tr', 'connect.facebook.net', 'facebook.net',
            'ads.yahoo.com', 'bing.com/ads', 'twitter.com/i/adsct',
            'linkedin.com/px', 'pinterest.com/ct', 'snapchat.com/px',
            'tiktok.com/i18n/pixel', 'reddit.com/api/v1/pixel',

            # CDNs for ads/tracking (be more specific)
            'cdn.segment.com', 'cdn.mxpnl.com', 'static.hotjar.com',

            # Common ad/tracking endpoints
            '/pixel.gif', '/collect?', '/tr?', '/ads/', '/ad/', '/tracking',
            '/analytics', '/metrics', '/telemetry', '/beacon', '/ping',

            # Specific tracking services
            'amplitude.com', 'intercom.io', 'zendesk.com/embeds',
            'olark.com', 'zopim.com', 'drift.com', 'crisp.chat'
        }

    def load(self, loader):
        """Configure addon options."""
        loader.add_option(
            "timeline_enabled", bool, True,
            "Enable API timeline generation"
        )
        loader.add_option(
            "timeline_output_dir", str, "api_timeline",
            "Directory to save timeline files"
        )
        loader.add_option(
            "timeline_custom_blocks", str, "",
            "Comma-separated list of additional patterns to block"
        )

    def configure(self, updated):
        """Handle configuration updates."""
        if "timeline_custom_blocks" in updated:
            custom_blocks = ctx.options.timeline_custom_blocks
            if custom_blocks:
                additional_patterns = [p.strip() for p in custom_blocks.split(',')]
                self.blocked_patterns.update(additional_patterns)
                logging.info(f"📝 Added {len(additional_patterns)} custom block patterns")

    def response(self, flow: http.HTTPFlow):
        """Process completed API calls for timeline."""
        if not ctx.options.timeline_enabled:
            return

        # Skip if this looks like ads/analytics
        if self._is_blocked_traffic(flow):
            return

        # Skip non-API looking traffic
        if not self._is_api_traffic(flow):
            return

        try:
            self._record_api_call(flow)
        except Exception as e:
            logging.error(f"Timeline recording failed for {flow.request.pretty_url}: {e}")

    def _is_blocked_traffic(self, flow: http.HTTPFlow) -> bool:
        """Check if this traffic should be blocked (ads/analytics)."""
        url = flow.request.pretty_url.lower()
        host = flow.request.pretty_host.lower()
        path = flow.request.path.lower()

        # Check against all blocked patterns
        for pattern in self.blocked_patterns:
            if pattern in url or pattern in host or pattern in path:
                return True

        # Additional heuristics for ads/analytics
        # Check for tracking query parameters
        tracking_params = ['utm_', 'fbclid', 'gclid', '_ga', 'mc_', 'mkt_']
        for param in tracking_params:
            if param in url:
                return True

        # Check for typical analytics request patterns
        if any(indicator in path for indicator in ['/collect', '/pixel', '/beacon', '/track']):
            return True

        return False

    def _is_api_traffic(self, flow: http.HTTPFlow) -> bool:
        """Determine if this looks like actual API traffic we care about."""
        url = flow.request.pretty_url.lower()
        path = flow.request.path.lower()

        # Strong API indicators
        api_indicators = [
            '/api/', '/v1/', '/v2/', '/v3/', '/v4/', '/rest/',
            '/graphql', '/rpc/', '/service/', '/endpoint/'
        ]

        for indicator in api_indicators:
            if indicator in path:
                return True

        # Check for API-like subdomains
        host = flow.request.pretty_host.lower()
        api_subdomains = ['api.', 'service.', 'backend.', 'data.', 'app.']
        for subdomain in api_subdomains:
            if host.startswith(subdomain):
                return True

        # Check response content type
        if flow.response and flow.response.headers:
            content_type = flow.response.headers.get('content-type', '').lower()
            if any(t in content_type for t in ['json', 'xml', 'api']):
                return True

        # Check for structured data in response
        if flow.response and flow.response.content:
            try:
                content = flow.response.get_text()[:500]  # First 500 chars
                if content and (content.strip().startswith('{') or content.strip().startswith('[')):
                    return True
            except:
                pass

        return False

    def _record_api_call(self, flow: http.HTTPFlow):
        """Record an API call for the timeline."""
        timestamp = getattr(flow.request, 'timestamp_start', time.time())

        # Calculate response time
        response_time = 0
        if flow.response and hasattr(flow.response, 'timestamp_start'):
            response_time = (flow.response.timestamp_start - timestamp) * 1000  # ms

        # Extract key information
        call_info = {
            'timestamp': timestamp,
            'datetime': datetime.fromtimestamp(timestamp).isoformat(),
            'method': flow.request.method,
            'url': flow.request.pretty_url,
            'host': flow.request.pretty_host,
            'path': flow.request.path,
            'status_code': flow.response.status_code if flow.response else None,
            'response_time_ms': round(response_time, 1),
            'response_size': len(flow.response.content) if flow.response and flow.response.content else 0,
            'content_type': flow.response.headers.get('content-type', '') if flow.response else '',
            'is_error': flow.response.status_code >= 400 if flow.response else False
        }

        self.api_calls.append(call_info)
        self.domains_seen.add(flow.request.pretty_host)

        # Log interesting calls
        if call_info['is_error']:
            logging.info(f"❌ API Error: {call_info['method']} {call_info['path']} → {call_info['status_code']}")
        elif response_time > 2000:  # > 2 seconds
            logging.info(f"🐌 Slow API: {call_info['method']} {call_info['path']} → {response_time:.1f}ms")

    def generate_timeline_files(self, output_dir: str = None):
        """Generate all timeline visualization files."""
        if not self.api_calls:
            logging.info("📊 No API calls recorded for timeline")
            return

        if output_dir is None:
            output_dir = ctx.options.timeline_output_dir

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        logging.info(f"📊 Generating timeline with {len(self.api_calls)} API calls...")

        # Generate different timeline formats
        self._generate_json_timeline(output_path)
        self._generate_html_timeline(output_path)
        self._generate_markdown_timeline(output_path)
        self._generate_csv_timeline(output_path)

        logging.info(f"✅ Timeline files generated in: {output_path.absolute()}")

    def _generate_json_timeline(self, output_path: Path):
        """Generate JSON timeline data."""
        timeline_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_calls': len(self.api_calls),
                'unique_domains': len(self.domains_seen),
                'time_range': {
                    'start': min(call['datetime'] for call in self.api_calls),
                    'end': max(call['datetime'] for call in self.api_calls)
                }
            },
            'domains': list(self.domains_seen),
            'timeline': self.api_calls
        }

        with open(output_path / 'timeline.json', 'w') as f:
            json.dump(timeline_data, f, indent=2)

    def _generate_html_timeline(self, output_path: Path):
        """Generate interactive HTML timeline."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>API Timeline Visualization</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; }}
        .header {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .stats {{ display: flex; gap: 20px; margin-bottom: 20px; }}
        .stat {{ background: white; padding: 15px; border-radius: 6px; border: 1px solid #e1e5e9; }}
        .timeline {{ background: white; border-radius: 8px; border: 1px solid #e1e5e9; }}
        .call {{ padding: 12px; border-bottom: 1px solid #f0f0f0; display: flex; align-items: center; gap: 15px; }}
        .call:hover {{ background: #f8f9fa; }}
        .timestamp {{ color: #666; font-size: 14px; width: 100px; }}
        .method {{ font-weight: bold; width: 60px; }}
        .method.GET {{ color: #28a745; }}
        .method.POST {{ color: #007bff; }}
        .method.PUT {{ color: #ffc107; }}
        .method.DELETE {{ color: #dc3545; }}
        .url {{ flex: 1; font-family: monospace; font-size: 14px; }}
        .status {{ width: 40px; text-align: center; }}
        .status.ok {{ color: #28a745; }}
        .status.error {{ color: #dc3545; font-weight: bold; }}
        .response-time {{ color: #666; width: 80px; }}
        .slow {{ color: #ffc107; font-weight: bold; }}
        .domain-filter {{ margin-bottom: 15px; }}
        .domain-filter select {{ padding: 8px; border-radius: 4px; border: 1px solid #ccc; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🕒 API Timeline Visualization</h1>
        <p>Chronological view of {len(self.api_calls)} API calls across {len(self.domains_seen)} domains</p>
    </div>

    <div class="stats">
        <div class="stat">
            <strong>{len(self.api_calls)}</strong><br>
            Total API Calls
        </div>
        <div class="stat">
            <strong>{len(self.domains_seen)}</strong><br>
            Unique Domains
        </div>
        <div class="stat">
            <strong>{len([c for c in self.api_calls if c['is_error']])}</strong><br>
            Error Responses
        </div>
        <div class="stat">
            <strong>{round(sum(c['response_time_ms'] for c in self.api_calls) / len(self.api_calls), 1)}ms</strong><br>
            Avg Response Time
        </div>
    </div>

    <div class="domain-filter">
        <label>Filter by domain: </label>
        <select id="domainFilter" onchange="filterByDomain()">
            <option value="">All domains</option>
            {''.join(f'<option value="{domain}">{domain}</option>' for domain in sorted(self.domains_seen))}
        </select>
    </div>

    <div class="timeline" id="timeline">
        {''.join(self._generate_html_call(call) for call in self.api_calls)}
    </div>

    <script>
        function filterByDomain() {{
            const filter = document.getElementById('domainFilter').value;
            const calls = document.querySelectorAll('.call');
            calls.forEach(call => {{
                const url = call.querySelector('.url').textContent;
                if (!filter || url.includes(filter)) {{
                    call.style.display = 'flex';
                }} else {{
                    call.style.display = 'none';
                }}
            }});
        }}
    </script>
</body>
</html>
"""

        with open(output_path / 'timeline.html', 'w') as f:
            f.write(html_content)

    def _generate_html_call(self, call: Dict) -> str:
        """Generate HTML for a single API call."""
        time_str = datetime.fromisoformat(call['datetime']).strftime('%H:%M:%S')
        status_class = 'error' if call['is_error'] else 'ok'
        time_class = 'slow' if call['response_time_ms'] > 1000 else ''

        return f"""
        <div class="call">
            <div class="timestamp">{time_str}</div>
            <div class="method {call['method']}">{call['method']}</div>
            <div class="url">{call['url']}</div>
            <div class="status {status_class}">{call['status_code'] or '?'}</div>
            <div class="response-time {time_class}">{call['response_time_ms']}ms</div>
        </div>
        """

    def _generate_markdown_timeline(self, output_path: Path):
        """Generate markdown timeline summary."""
        md_content = [
            "# 🕒 API Timeline Summary",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total API Calls:** {len(self.api_calls)}",
            f"**Unique Domains:** {len(self.domains_seen)}",
            "",
            "## 📊 Statistics",
            ""
        ]

        # Domain statistics
        domain_counts = defaultdict(int)
        for call in self.api_calls:
            domain_counts[call['host']] += 1

        md_content.extend([
            "### Top Domains:",
            ""
        ])

        for domain, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            md_content.append(f"- **{domain}**: {count} calls")

        # Method statistics
        method_counts = defaultdict(int)
        for call in self.api_calls:
            method_counts[call['method']] += 1

        md_content.extend([
            "",
            "### HTTP Methods:",
            ""
        ])

        for method, count in sorted(method_counts.items()):
            md_content.append(f"- **{method}**: {count} calls")

        # Error summary
        errors = [call for call in self.api_calls if call['is_error']]
        if errors:
            md_content.extend([
                "",
                "### ❌ Error Responses:",
                ""
            ])

            for error in errors[:10]:  # Show first 10 errors
                time_str = datetime.fromisoformat(error['datetime']).strftime('%H:%M:%S')
                md_content.append(f"- `{time_str}` **{error['status_code']}** {error['method']} {error['path']}")

        # Recent calls (last 20)
        md_content.extend([
            "",
            "## 🕒 Recent API Calls (Latest 20)",
            "",
            "| Time | Method | URL | Status | Response Time |",
            "|------|--------|-----|--------|---------------|"
        ])

        for call in self.api_calls[-20:]:
            time_str = datetime.fromisoformat(call['datetime']).strftime('%H:%M:%S')
            status = call['status_code'] or '?'
            md_content.append(f"| {time_str} | {call['method']} | `{call['path']}` | {status} | {call['response_time_ms']}ms |")

        with open(output_path / 'timeline.md', 'w') as f:
            f.write('\n'.join(md_content))

    def _generate_csv_timeline(self, output_path: Path):
        """Generate CSV timeline for data analysis."""
        import csv

        with open(output_path / 'timeline.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'timestamp', 'datetime', 'method', 'host', 'path', 'url',
                'status_code', 'response_time_ms', 'response_size', 'content_type', 'is_error'
            ])
            writer.writeheader()
            writer.writerows(self.api_calls)

    def get_timeline_summary(self) -> Dict[str, Any]:
        """Get timeline summary for external use."""
        if not self.api_calls:
            return {'total_calls': 0}

        return {
            'total_calls': len(self.api_calls),
            'unique_domains': len(self.domains_seen),
            'error_count': len([c for c in self.api_calls if c['is_error']]),
            'avg_response_time': sum(c['response_time_ms'] for c in self.api_calls) / len(self.api_calls),
            'domains': list(self.domains_seen),
            'time_range': {
                'start': min(call['datetime'] for call in self.api_calls),
                'end': max(call['datetime'] for call in self.api_calls)
            }
        }


# Register the addon
addons = [APITimeline()]
