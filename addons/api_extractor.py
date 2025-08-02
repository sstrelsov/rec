#!/usr/bin/env python3
"""
api_extractor.py - Advanced API Documentation Generator

Automatically extracts and documents API schemas, parameters, and responses
to create comprehensive API documentation from captured traffic.

Filters out annoying ads/analytics traffic.
"""

import json
import re
import logging
from collections import defaultdict
from typing import Dict, List, Any, Set, Optional
from urllib.parse import urlparse, parse_qs
from mitmproxy import http, ctx


class APIExtractor:
    """Advanced API documentation generator from captured traffic."""

    def __init__(self):
        self.api_catalog = defaultdict(lambda: {
            'endpoints': defaultdict(lambda: {
                'methods': defaultdict(lambda: {
                    'count': 0,
                    'parameters': {'query': set(), 'path': set(), 'headers': set(), 'body_fields': set()},
                    'request_examples': [],
                    'response_schemas': defaultdict(int),  # Schema -> count
                    'status_codes': defaultdict(int),
                    'response_examples': {},
                    'content_types': {'request': set(), 'response': set()}
                })
            }),
            'base_url': '',
            'total_calls': 0
        })

        # Ads/Analytics blocklist
        self.blocked_patterns = {
            'google-analytics.com', 'googleanalytics.com', 'google-analytics',
            'gtag', 'gtm.js', 'ga.js', '_ga', '/analytics/', '/tracking/',
            'mixpanel.com', 'amplitude.com', 'segment.com', 'segment.io',
            'hotjar.com', 'fullstory.com', 'logrocket.com', 'datadog',
            'googlesyndication.com', 'doubleclick.net', 'googleadservices.com',
            'facebook.com/tr', 'connect.facebook.net', 'facebook.net',
            '/pixel.gif', '/collect?', '/tr?', '/ads/', '/ad/', '/tracking',
            '/analytics', '/metrics', '/telemetry', '/beacon', '/ping'
        }

        # Schema detection patterns
        self.common_id_patterns = [
            (r'\d+', '{id}'),
            (r'[a-f0-9-]{36}', '{uuid}'),
            (r'[a-f0-9]{24}', '{objectId}'),
            (r'\w{20,}', '{token}')
        ]

    def load(self, loader):
        """Configure addon options."""
        loader.add_option(
            "api_extractor_enabled", bool, True,
            "Enable automatic API documentation extraction"
        )
        loader.add_option(
            "extractor_min_calls", int, 2,
            "Minimum calls per endpoint to include in documentation"
        )
        loader.add_option(
            "extractor_example_limit", int, 3,
            "Maximum number of examples to store per endpoint"
        )

    def response(self, flow: http.HTTPFlow):
        """Process completed API calls."""
        if not self._get_options_value("api_extractor_enabled", True):
            return

        # Skip ads/analytics traffic first
        if self._is_blocked_traffic(flow):
            return

        # Skip non-API traffic (basic heuristics)
        if not self._is_api_request(flow):
            return

        try:
            self._extract_api_info(flow)
        except Exception as e:
            logging.warning(f"API extraction failed for {flow.request.pretty_url}: {e}")

    def _is_blocked_traffic(self, flow: http.HTTPFlow) -> bool:
        """Check if this traffic should be blocked (ads/analytics)."""
        url = flow.request.pretty_url.lower()
        host = flow.request.pretty_host.lower()
        path = flow.request.path.lower()

        # Check against blocked patterns
        for pattern in self.blocked_patterns:
            if pattern in url or pattern in host or pattern in path:
                return True

        # Check for tracking query parameters
        tracking_params = ['utm_', 'fbclid', 'gclid', '_ga', 'mc_', 'mkt_']
        for param in tracking_params:
            if param in url:
                return True

        return False

    def _is_api_request(self, flow: http.HTTPFlow) -> bool:
        """Determine if this is an API request worth documenting."""
        # Skip ads/analytics first
        if self._is_blocked_traffic(flow):
            return False

        url = flow.request.pretty_url
        path = flow.request.path
        method = flow.request.method

        # Skip static files
        static_extensions = ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.woff', '.woff2', '.ttf']
        if any(path.lower().endswith(ext) for ext in static_extensions):
            return False

        # Skip HTML pages (usually not APIs)
        if path.lower().endswith('.html') or path == '/':
            return False

        # Look for API patterns
        api_patterns = ['/api/', '/v1/', '/v2/', '/v3/', '/rest/', '/graphql', '/json', '/svc/']
        if any(pattern in path.lower() for pattern in api_patterns):
            return True

        # JSON responses are likely APIs
        if hasattr(flow, 'response') and flow.response:
            content_type = flow.response.headers.get('content-type', '').lower()
            if 'application/json' in content_type:
                return True

        return False

    def _get_options_value(self, option_name: str, default_value):
        """Get option value with fallback for offline mode."""
        try:
            from mitmproxy import ctx
            if hasattr(ctx, 'options') and hasattr(ctx.options, option_name):
                return getattr(ctx.options, option_name)
        except:
            pass
        return default_value

    def _extract_api_info(self, flow: http.HTTPFlow):
        """Extract comprehensive API information."""
        # Parse URL components
        parsed_url = urlparse(flow.request.pretty_url)
        domain = parsed_url.netloc
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)

        # Normalize path for grouping
        normalized_path = self._normalize_path(path)

        # Get API catalog entry
        api = self.api_catalog[domain]
        api['base_url'] = f"{parsed_url.scheme}://{parsed_url.netloc}"
        api['total_calls'] += 1

        endpoint = api['endpoints'][normalized_path]
        method_data = endpoint['methods'][flow.request.method]
        method_data['count'] += 1

        # Extract parameters
        self._extract_parameters(flow, method_data, query_params, normalized_path, path)

        # Extract request information
        self._extract_request_info(flow, method_data)

        # Extract response information
        self._extract_response_info(flow, method_data)

    def _normalize_path(self, path: str) -> str:
        """Normalize API path by replacing dynamic segments."""
        normalized = path

        # Apply ID patterns
        for pattern, replacement in self.common_id_patterns:
            normalized = re.sub(f'/{pattern}', f'/{replacement}', normalized)

        # Handle query parameters in path (shouldn't happen but...)
        normalized = normalized.split('?')[0]

        # Clean up path
        normalized = normalized.rstrip('/')
        return normalized or '/'

    def _extract_parameters(self, flow: http.HTTPFlow, method_data: Dict,
                          query_params: Dict, normalized_path: str, original_path: str):
        """Extract parameter information."""
        params = method_data['parameters']

        # Query parameters
        for param_name in query_params.keys():
            params['query'].add(param_name)

        # Path parameters (compare normalized vs original)
        if normalized_path != original_path:
            # Extract path parameter names from the difference
            norm_parts = normalized_path.split('/')
            orig_parts = original_path.split('/')

            for i, (norm_part, orig_part) in enumerate(zip(norm_parts, orig_parts)):
                if norm_part.startswith('{') and norm_part.endswith('}'):
                    param_name = norm_part[1:-1]  # Remove braces
                    params['path'].add(param_name)

        # Header parameters (common API headers)
        api_headers = ['authorization', 'x-api-key', 'x-auth-token', 'content-type', 'accept']
        for header in api_headers:
            if header in flow.request.headers:
                params['headers'].add(header)

        # Body parameters (if JSON)
        if flow.request.content and flow.request.method in ['POST', 'PUT', 'PATCH']:
            try:
                content_type = flow.request.headers.get('content-type', '').lower()
                if 'json' in content_type:
                    body_text = flow.request.get_text()
                    if body_text:
                        body_data = json.loads(body_text)
                        self._extract_json_fields(body_data, params['body_fields'])
            except:
                pass

    def _extract_json_fields(self, data: Any, field_set: Set[str], prefix: str = ''):
        """Recursively extract field names from JSON data."""
        if isinstance(data, dict):
            for key, value in data.items():
                field_name = f"{prefix}.{key}" if prefix else key
                field_set.add(field_name)

                # Recurse into nested objects (limit depth)
                if isinstance(value, (dict, list)) and prefix.count('.') < 2:
                    self._extract_json_fields(value, field_set, field_name)

        elif isinstance(data, list) and data:
            # Process first item in array as example
            if prefix.count('.') < 2:
                self._extract_json_fields(data[0], field_set, prefix)

    def _extract_request_info(self, flow: http.HTTPFlow, method_data: Dict):
        """Extract request information and examples."""
        content_type = flow.request.headers.get('content-type', '').lower()
        method_data['content_types']['request'].add(content_type)

        # Store request examples (limited)
        if len(method_data['request_examples']) < self._get_options_value("extractor_example_limit", 3):
            example = {
                'headers': dict(flow.request.headers),
                'content_type': content_type
            }

            # Add body if present and JSON
            if flow.request.content and 'json' in content_type:
                try:
                    body_text = flow.request.get_text()
                    if body_text:
                        example['body'] = json.loads(body_text)
                except:
                    example['body'] = '<non-json data>'

            method_data['request_examples'].append(example)

    def _extract_response_info(self, flow: http.HTTPFlow, method_data: Dict):
        """Extract response information and schemas."""
        if not flow.response:
            return

        # Status codes
        status_code = flow.response.status_code
        method_data['status_codes'][status_code] += 1

        # Content type
        content_type = flow.response.headers.get('content-type', '').lower()
        method_data['content_types']['response'].add(content_type)

        # Response schema and examples
        if flow.response.content and 'json' in content_type:
            try:
                response_text = flow.response.get_text()
                if response_text:
                    response_data = json.loads(response_text)

                    # Generate schema signature
                    schema = self._generate_schema_signature(response_data)
                    method_data['response_schemas'][schema] += 1

                    # Store example (one per status code)
                    if status_code not in method_data['response_examples']:
                        method_data['response_examples'][status_code] = {
                            'headers': dict(flow.response.headers),
                            'body': response_data
                        }

            except Exception as e:
                logging.debug(f"Failed to parse JSON response: {e}")

    def _generate_schema_signature(self, data: Any, depth: int = 0) -> str:
        """Generate a schema signature for response structure."""
        if depth > 3:  # Limit recursion depth
            return "..."

        if isinstance(data, dict):
            if not data:
                return "{}"
            fields = []
            for key, value in sorted(data.items()):
                value_sig = self._generate_schema_signature(value, depth + 1)
                fields.append(f"{key}:{value_sig}")
            return "{" + ",".join(fields) + "}"

        elif isinstance(data, list):
            if not data:
                return "[]"
            # Use first item as template
            item_sig = self._generate_schema_signature(data[0], depth + 1)
            return f"[{item_sig}]"

        elif isinstance(data, str):
            return "string"
        elif isinstance(data, int):
            return "number"
        elif isinstance(data, float):
            return "number"
        elif isinstance(data, bool):
            return "boolean"
        elif data is None:
            return "null"
        else:
            return "unknown"

    def export_documentation(self, output_dir: str = "api_docs"):
        """Export comprehensive API documentation."""
        from pathlib import Path

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # Generate documentation for each domain
        for domain, api_data in self.api_catalog.items():
            if api_data['total_calls'] < self._get_options_value("extractor_min_calls", 2):
                continue

            domain_dir = output_path / self._sanitize_filename(domain)
            domain_dir.mkdir(exist_ok=True)

            # Generate OpenAPI spec
            openapi_spec = self._generate_openapi_spec(domain)

            # Save as JSON
            with open(domain_dir / "openapi.json", 'w') as f:
                json.dump(openapi_spec, f, indent=2)

            # Generate summary report
            self._generate_summary_report(domain, api_data, domain_dir)

            logging.info(f"📚 Generated API documentation for {domain} in {domain_dir}")

    def _generate_openapi_spec(self, domain: str) -> Dict[str, Any]:
        """Generate OpenAPI 3.0 specification from captured APIs."""
        api_data = self.api_catalog[domain]
        min_calls = self._get_options_value("extractor_min_calls", 2)

        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": f"API Documentation: {domain}",
                "version": "1.0.0",
                "description": "API documentation generated from captured traffic"
            },
            "servers": [{"url": api_data['base_url']}] if api_data['base_url'] else [],
            "paths": {}
        }

        # Process endpoints
        for path, endpoint_data in api_data['endpoints'].items():
            path_spec = {}

            for method, method_data in endpoint_data['methods'].items():
                if method_data['count'] < min_calls:
                    continue

                # Build method specification
                method_spec = {
                    "summary": f"{method} {path}",
                    "description": f"Captured {method_data['count']} calls",
                    "parameters": [],
                    "responses": {}
                }

                # Add parameters
                params = method_data['parameters']

                # Query parameters
                for param in params['query']:
                    method_spec["parameters"].append({
                        "name": param,
                        "in": "query",
                        "schema": {"type": "string"}
                    })

                # Path parameters
                for param in params['path']:
                    method_spec["parameters"].append({
                        "name": param,
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"}
                    })

                # Request body (for POST/PUT/PATCH)
                if method in ['POST', 'PUT', 'PATCH'] and method_data['request_examples']:
                    example = method_data['request_examples'][0]
                    if 'body' in example:
                        method_spec["requestBody"] = {
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"},
                                    "example": example['body']
                                }
                            }
                        }

                # Responses
                for status_code, count in method_data['status_codes'].items():
                    response_spec = {"description": f"Response (seen {count} times)"}

                    if status_code in method_data['response_examples']:
                        example = method_data['response_examples'][status_code]
                        response_spec["content"] = {
                            "application/json": {
                                "schema": {"type": "object"},
                                "example": example['body']
                            }
                        }

                    method_spec["responses"][str(status_code)] = response_spec

                path_spec[method.lower()] = method_spec

            if path_spec:
                spec["paths"][path] = path_spec

        return spec

    def _generate_summary_report(self, domain: str, api_data: Dict, output_dir):
        """Generate human-readable summary report."""
        report = [
            f"# API Documentation: {domain}",
            f"",
            f"**Base URL:** {api_data['base_url']}",
            f"**Total API Calls:** {api_data['total_calls']}",
            f"**Endpoints Discovered:** {len(api_data['endpoints'])}",
            f"",
            f"## Endpoints",
            f""
        ]

        for path, endpoint_data in sorted(api_data['endpoints'].items()):
            total_calls = sum(m['count'] for m in endpoint_data['methods'].values())
            methods = list(endpoint_data['methods'].keys())

            report.extend([
                f"### {path}",
                f"",
                f"**Methods:** {', '.join(methods)}",
                f"**Total Calls:** {total_calls}",
                f""
            ])

            for method, method_data in endpoint_data['methods'].items():
                if method_data['count'] < self._get_options_value("extractor_min_calls", 2):
                    continue

                report.extend([
                    f"#### {method} {path}",
                    f"",
                    f"**Calls:** {method_data['count']}",
                    f"**Status Codes:** {dict(method_data['status_codes'])}",
                    f""
                ])

                # Parameters
                params = method_data['parameters']
                if any(params.values()):
                    report.append("**Parameters:**")
                    if params['path']:
                        report.append(f"- Path: {', '.join(params['path'])}")
                    if params['query']:
                        report.append(f"- Query: {', '.join(params['query'])}")
                    if params['headers']:
                        report.append(f"- Headers: {', '.join(params['headers'])}")
                    if params['body_fields']:
                        report.append(f"- Body: {', '.join(list(params['body_fields'])[:10])}")
                    report.append("")

        with open(output_dir / "README.md", 'w') as f:
            f.write('\n'.join(report))

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize name for filesystem use."""
        return re.sub(r'[^\w\-.]', '_', name)


# Register the addon
addons = [APIExtractor()]
