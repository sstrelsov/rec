#!/usr/bin/env python3
"""
api_timeline.py - API Timeline Visualization

Generates chronological timeline of API calls with interactive filtering.
Configurable filtering based on HTTP methods, request types, and noise reduction.
"""

import json
import time
import logging
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Set
from mitmproxy import http, ctx
import sys
sys.path.append('.')

from addons.context_detector import detect_request_context, RequestContext, get_context_info
from config import config


class APITimeline:
    """
    Chronological timeline generator for API calls with configurable filtering.
    """

    def __init__(self):
        self.api_calls = []
        self.domains_seen = set()

    def response(self, flow: http.HTTPFlow):
        """Process completed requests based on configuration."""
        # Skip ads/analytics traffic first
        if self._is_blocked_traffic(flow):
            return

        # Apply configurable filtering
        if not self._should_include_request(flow):
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
        for pattern in config.blocked_patterns:
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

    def _should_include_request(self, flow: http.HTTPFlow) -> bool:
        """Determine if request should be included based on configuration."""
        method = flow.request.method.upper()

        # Check HTTP method filtering
        if method not in config.http_methods:
            return False

        # Check context-based filtering
        context = detect_request_context(flow)

        if context == RequestContext.BROWSER and not config.include_browser_requests:
            return False
        elif context == RequestContext.FRONTEND_BACKEND and not config.include_api_requests:
            return False
        elif context == RequestContext.UNKNOWN and not config.include_unknown_requests:
            return False

        # Apply noise filtering based on config
        if self._is_filtered_noise(flow):
            return False

        return True

    def _is_filtered_noise(self, flow: http.HTTPFlow) -> bool:
        """Check if request should be filtered as noise based on config."""
        method = flow.request.method.upper()
        path = flow.request.path.lower()

        # Static assets filtering
        if config.filter_static_assets:
            static_extensions = ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.woff', '.woff2', '.ttf']
            if any(path.endswith(ext) for ext in static_extensions):
                return True

        # Browser housekeeping filtering
        if config.filter_browser_housekeeping:
            housekeeping_patterns = [
                '/favicon.ico', '/robots.txt', '/sitemap.xml',
                '/apple-touch-icon', '/manifest.json', '/.well-known/'
            ]
            if any(pattern in path for pattern in housekeeping_patterns):
                return True

        # Health checks filtering
        if config.filter_health_checks:
            health_patterns = ['/ping', '/healthz', '/health', '/status', '/alive', '/ready']
            if any(pattern in path for pattern in health_patterns):
                return True

        # Prefetch/preload filtering
        if config.filter_prefetch_requests:
            if flow.request.headers.get('purpose') in ['prefetch', 'preload']:
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

        # Detect request context
        context = detect_request_context(flow)
        context_info = get_context_info(context)

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
            'is_error': flow.response.status_code >= 400 if flow.response else False,
            'context': context.value,
            'context_name': context_info['name'],
            'context_icon': context_info['icon'],
            'context_description': context_info['description']
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
        """Generate interactive HTML timeline with configurable filtering."""
        # Get unique methods and domains from the data
        unique_methods = sorted(set(call['method'] for call in self.api_calls))
        unique_domains = sorted(self.domains_seen)

        # Generate method checkboxes based on config
        method_checkboxes = []
        for method in unique_methods:
            checked = "checked" if method in config.http_methods else ""
            method_checkboxes.append(f'<label><input type="checkbox" value="{method}" {checked} onchange="applyFilters()"> {method}</label>')

        # Generate context checkboxes based on config
        context_checkboxes = []
        context_options = [
            ("browser", "🌐 Browser", config.include_browser_requests),
            ("api", "⚡ API", config.include_api_requests),
            ("unknown", "❓ Unknown", config.include_unknown_requests)
        ]
        for value, label, enabled in context_options:
            checked = "checked" if enabled else ""
            context_checkboxes.append(f'<label><input type="checkbox" value="{value}" {checked} onchange="applyFilters()"> {label}</label>')

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>API Timeline Visualization</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0; padding: 20px; background: #f8f9fa;
        }}
        .header {{
            background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;
            border: 1px solid #e1e5e9;
        }}
        .stats {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px; margin-bottom: 20px;
        }}
        .stat {{
            background: white; padding: 15px; border-radius: 6px;
            border: 1px solid #e1e5e9; text-align: center;
        }}
        .filters {{
            background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;
            border: 1px solid #e1e5e9;
        }}
        .filter-section {{
            margin-bottom: 15px;
        }}
        .filter-section h4 {{
            margin: 0 0 10px 0; color: #333;
        }}
        .checkbox-group {{
            display: flex; flex-wrap: wrap; gap: 15px;
        }}
        .checkbox-group label {{
            display: flex; align-items: center; gap: 5px; cursor: pointer;
        }}
        .timeline {{
            background: white; border-radius: 8px; border: 1px solid #e1e5e9;
            max-height: 70vh; overflow-y: auto;
        }}
        .call {{
            padding: 12px 15px; border-bottom: 1px solid #f0f0f0;
            display: grid; grid-template-columns: 100px 40px 60px 1fr 50px 80px;
            gap: 15px; align-items: center;
        }}
        .call:hover {{ background: #f8f9fa; }}
        .call.hidden {{ display: none; }}
        .timestamp {{ color: #666; font-size: 13px; }}
        .context {{ text-align: center; font-size: 16px; }}
        .method {{ font-weight: bold; text-align: center; }}
        .method.GET {{ color: #28a745; }}
        .method.POST {{ color: #007bff; }}
        .method.PUT {{ color: #ffc107; color: #000; }}
        .method.PATCH {{ color: #17a2b8; }}
        .method.DELETE {{ color: #dc3545; }}
        .url {{
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 13px; overflow: hidden; text-overflow: ellipsis;
        }}
        .status {{ text-align: center; font-weight: bold; }}
        .status.ok {{ color: #28a745; }}
        .status.error {{ color: #dc3545; }}
        .response-time {{ color: #666; text-align: right; }}
        .slow {{ color: #ffc107; font-weight: bold; }}
        .filter-summary {{
            background: #e3f2fd; padding: 10px; border-radius: 4px;
            margin-top: 15px; font-size: 14px;
        }}
        .reset-filters {{
            background: #dc3545; color: white; border: none; padding: 8px 15px;
            border-radius: 4px; cursor: pointer; margin-left: 15px;
        }}
        .reset-filters:hover {{ background: #c82333; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🕒 API Timeline Visualization</h1>
        <p>Chronological view of <span id="total-calls">{len(self.api_calls)}</span> requests across {len(self.domains_seen)} domains</p>
    </div>

    <div class="stats">
        <div class="stat">
            <strong>{len(self.api_calls)}</strong><br>
            <small>Total Requests</small>
        </div>
        <div class="stat">
            <strong>{len(self.domains_seen)}</strong><br>
            <small>Unique Domains</small>
        </div>
        <div class="stat">
            <strong>{len([c for c in self.api_calls if c['is_error']])}</strong><br>
            <small>Error Responses</small>
        </div>
        <div class="stat">
            <strong>{round(sum(c['response_time_ms'] for c in self.api_calls) / len(self.api_calls), 1) if self.api_calls else 0}ms</strong><br>
            <small>Avg Response Time</small>
        </div>
        <div class="stat">
            <strong>{len([c for c in self.api_calls if c.get('context') == 'browser'])}</strong><br>
            <small>🌐 Browser</small>
        </div>
        <div class="stat">
            <strong>{len([c for c in self.api_calls if c.get('context') == 'api'])}</strong><br>
            <small>⚡ API</small>
        </div>
    </div>

    <div class="filters">
        <div class="filter-section">
            <h4>🔧 HTTP Methods</h4>
            <div class="checkbox-group" id="method-filters">
                {' '.join(method_checkboxes)}
            </div>
        </div>

        <div class="filter-section">
            <h4>🎯 Request Context</h4>
            <div class="checkbox-group" id="context-filters">
                {' '.join(context_checkboxes)}
            </div>
        </div>

        <div class="filter-section">
            <h4>🌐 Domain Filter</h4>
            <select id="domain-filter" onchange="applyFilters()" style="padding: 8px; border-radius: 4px;">
                <option value="">All domains ({len(unique_domains)})</option>
                {''.join(f'<option value="{domain}">{domain}</option>' for domain in unique_domains)}
            </select>
            <button class="reset-filters" onclick="resetFilters()">Reset All Filters</button>
        </div>

        <div class="filter-summary" id="filter-summary">
            Showing <span id="visible-count">{len(self.api_calls)}</span> of {len(self.api_calls)} requests
        </div>
    </div>

    <div class="timeline" id="timeline">
        {''.join(self._generate_html_call(call) for call in self.api_calls)}
    </div>

    <script>
        let allCalls = {json.dumps(self.api_calls)};

        function applyFilters() {{
            // Get selected methods
            const methodCheckboxes = document.querySelectorAll('#method-filters input[type="checkbox"]');
            const selectedMethods = Array.from(methodCheckboxes)
                .filter(cb => cb.checked)
                .map(cb => cb.value);

            // Get selected contexts
            const contextCheckboxes = document.querySelectorAll('#context-filters input[type="checkbox"]');
            const selectedContexts = Array.from(contextCheckboxes)
                .filter(cb => cb.checked)
                .map(cb => cb.value);

            // Get selected domain
            const domainFilter = document.getElementById('domain-filter').value;

            // Apply filters to all calls
            const calls = document.querySelectorAll('.call');
            let visibleCount = 0;

            calls.forEach((call, index) => {{
                const callData = allCalls[index];
                let show = true;

                // Method filter
                if (selectedMethods.length > 0 && !selectedMethods.includes(callData.method)) {{
                    show = false;
                }}

                // Context filter
                if (selectedContexts.length > 0 && !selectedContexts.includes(callData.context || 'unknown')) {{
                    show = false;
                }}

                // Domain filter
                if (domainFilter && !callData.url.includes(domainFilter)) {{
                    show = false;
                }}

                if (show) {{
                    call.classList.remove('hidden');
                    visibleCount++;
                }} else {{
                    call.classList.add('hidden');
                }}
            }});

            // Update summary
            document.getElementById('visible-count').textContent = visibleCount;
        }}

        function resetFilters() {{
            // Reset all checkboxes to config defaults
            const methodCheckboxes = document.querySelectorAll('#method-filters input[type="checkbox"]');
            const configMethods = {json.dumps(config.http_methods)};
            methodCheckboxes.forEach(cb => {{
                cb.checked = configMethods.includes(cb.value);
            }});

            // Reset context checkboxes to config defaults
            document.querySelector('#context-filters input[value="browser"]').checked = {json.dumps(config.include_browser_requests)};
            document.querySelector('#context-filters input[value="api"]').checked = {json.dumps(config.include_api_requests)};
            document.querySelector('#context-filters input[value="unknown"]').checked = {json.dumps(config.include_unknown_requests)};

            // Reset domain filter
            document.getElementById('domain-filter').value = '';

            // Apply filters
            applyFilters();
        }}

        // Apply initial filters based on config
        document.addEventListener('DOMContentLoaded', function() {{
            applyFilters();
        }});
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

        context = call.get('context', 'unknown')
        context_icon = call.get('context_icon', '❓')
        context_class = f'context {context}'

        return f"""
        <div class="call" data-context="{context}" data-method="{call['method']}" title="{call.get('context_description', '')}">
            <div class="timestamp">{time_str}</div>
            <div class="{context_class}">{context_icon}</div>
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
        context_counts = defaultdict(int)
        for call in self.api_calls:
            domain_counts[call['host']] += 1
            context_counts[call.get('context', 'unknown')] += 1

        md_content.extend([
            "### Top Domains:",
            ""
        ])

        for domain, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            md_content.append(f"- **{domain}**: {count} calls")

        # Context statistics
        md_content.extend([
            "",
            "### Request Context:",
            ""
        ])

        for context, count in sorted(context_counts.items()):
            icon = "🌐" if context == "browser" else "⚡" if context == "api" else "❓"
            md_content.append(f"- **{icon} {context.title()}**: {count} calls")

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
            "| Time | Context | Method | URL | Status | Response Time |",
            "|------|---------|--------|-----|--------|---------------|"
        ])

        for call in self.api_calls[-20:]:
            time_str = datetime.fromisoformat(call['datetime']).strftime('%H:%M:%S')
            status = call['status_code'] or '?'
            context_icon = call.get('context_icon', '❓')
            md_content.append(f"| {time_str} | {context_icon} | {call['method']} | `{call['path']}` | {status} | {call['response_time_ms']}ms |")

        with open(output_path / 'timeline.md', 'w') as f:
            f.write('\n'.join(md_content))

    def _generate_csv_timeline(self, output_path: Path):
        """Generate CSV timeline for data analysis."""
        import csv

        with open(output_path / 'timeline.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'timestamp', 'datetime', 'method', 'host', 'path', 'url',
                'status_code', 'response_time_ms', 'response_size', 'content_type', 'is_error',
                'context', 'context_name', 'context_icon', 'context_description'
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
