#!/usr/bin/env python3
"""
api_extractor.py - API Documentation Generator

Automatically extracts and documents API schemas, parameters, and responses
to create comprehensive API documentation from captured traffic.

Uses configurable filtering to focus on relevant APIs.
"""

import json
import re
import logging
from collections import defaultdict
from typing import Dict, List, Any, Set, Optional
from urllib.parse import urlparse, parse_qs
from mitmproxy import http, ctx
import sys
import os
import time

# Add parent directory to path to find config module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from addons.context_detector import detect_request_context, RequestContext, get_context_info
from config import config
from domain_utils import extract_root_domain, get_domain_hierarchy


class APIExtractor:
    """Advanced API documentation generator from captured traffic."""

    def __init__(self):
        # Organize APIs by root domain, then by full domain
        self.api_catalog = defaultdict(lambda: {
            'domains': defaultdict(lambda: {
                'endpoints': defaultdict(lambda: {
                    'methods': defaultdict(lambda: {
                        'count': 0,
                        'parameters': {'query': set(), 'path': set(), 'headers': set(), 'body_fields': set()},
                        'request_examples': [],
                        'response_schemas': defaultdict(int),  # Schema -> count
                        'status_codes': defaultdict(int),
                        'response_examples': {},
                        'content_types': {'request': set(), 'response': set()},
                        'contexts': defaultdict(int)  # Track request contexts
                    })
                }),
                'base_url': '',
                'total_calls': 0,
                'context_stats': defaultdict(int)
            }),
            'total_calls': 0,
            'context_stats': defaultdict(int)
        })

        # Ads/Analytics blocklist


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
            "extractor_min_calls", int, 1,
            "Minimum calls per endpoint to include in documentation"
        )
        loader.add_option(
            "extractor_example_limit", int, 3,
            "Maximum number of examples to store per endpoint"
        )

    def response(self, flow: http.HTTPFlow):
        """Process completed API calls."""
        if not config.api_extractor_enabled:
            return

        # Check if request should be included based on configuration
        if not self._should_include_request(flow):
            return

        # Skip ads/analytics traffic first
        if self._is_blocked_traffic(flow):
            return

        # Apply configurable noise filtering
        if self._is_filtered_noise(flow):
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
        for pattern in config.blocked_patterns:
            if pattern in url or pattern in host or pattern in path:
                return True

        # Check for tracking query parameters
        tracking_params = ['utm_', 'fbclid', 'gclid', '_ga', 'mc_', 'mkt_']
        for param in tracking_params:
            if param in url:
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
        if context == RequestContext.FRONTEND_BACKEND and not config.include_api_requests:
            return False
        if context == RequestContext.UNKNOWN and not config.include_unknown_requests:
            return False

        return True

    def _is_filtered_noise(self, flow: http.HTTPFlow) -> bool:
        """Check if request should be filtered as noise based on config."""
        method = flow.request.method.upper()
        path = flow.request.path.lower()

        if method == 'HEAD' and config.filter_health_checks:
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

    def _extract_api_info(self, flow: http.HTTPFlow):
        """Extract comprehensive API information."""
        # Parse URL components
        parsed_url = urlparse(flow.request.pretty_url)
        domain = parsed_url.netloc
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)

        # Get domain hierarchy information
        domain_info = get_domain_hierarchy(domain)
        root_domain = domain_info['root_domain']

        # Normalize path for grouping
        normalized_path = self._normalize_path(path)

        # Get API catalog entry (organized by root domain, then full domain)
        root_api = self.api_catalog[root_domain]
        root_api['total_calls'] += 1

        api = root_api['domains'][domain]
        api['base_url'] = f"{parsed_url.scheme}://{parsed_url.netloc}"
        api['total_calls'] += 1

        endpoint = api['endpoints'][normalized_path]
        method_data = endpoint['methods'][flow.request.method]
        method_data['count'] += 1

        # Track request context
        context = detect_request_context(flow)
        method_data['contexts'][context.value] += 1
        api['context_stats'][context.value] += 1
        root_api['context_stats'][context.value] += 1

        # Extract parameters
        self._extract_parameters(flow, method_data, query_params, normalized_path, path)

        # Extract request information
        self._extract_request_info(flow, method_data)

        # Extract response information
        self._extract_response_info(flow, method_data)

    def _normalize_path(self, path: str) -> str:
        """Normalize API path by replacing dynamic segments."""
        normalized = path

        # Apply ID patterns - match entire path segments
        for pattern, replacement in self.common_id_patterns:
            # Match entire path segments that fit the pattern
            normalized = re.sub(f'/({pattern})(?=/|$)', f'/{replacement}', normalized)

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
        
        # Store query parameter examples
        if 'query_examples' not in method_data:
            method_data['query_examples'] = {}
        for param_name, param_values in query_params.items():
            if param_values:  # Only store if there are values
                method_data['query_examples'][param_name] = param_values[0]  # Use first value

        # Path parameters (compare normalized vs original)
        if normalized_path != original_path:
            # Extract path parameter names from the difference
            norm_parts = normalized_path.split('/')
            orig_parts = original_path.split('/')

            # Store path parameter examples
            if 'path_examples' not in method_data:
                method_data['path_examples'] = {}

            for i, (norm_part, orig_part) in enumerate(zip(norm_parts, orig_parts)):
                if norm_part.startswith('{') and norm_part.endswith('}'):
                    param_name = norm_part[1:-1]  # Remove braces
                    params['path'].add(param_name)
                    # Store the actual value as example
                    method_data['path_examples'][param_name] = orig_part

        # Header parameters (common API headers + auth) - case insensitive matching
        common_headers = [
            'authorization', 'bearer', 'content-type', 'accept', 
            'user-agent', 'referer', 'origin'
        ]

        # Convert request headers to lowercase for case-insensitive matching
        request_headers_lower = {k.lower(): k for k in flow.request.headers.keys()}

        # Add common headers
        for header in common_headers:
            if header.lower() in request_headers_lower:
                params['headers'].add(header)
        
        # Add all x-* headers (API keys, tokens, custom headers)
        for header_lower, original_header in request_headers_lower.items():
            if header_lower.startswith('x-'):
                params['headers'].add(header_lower)

        # Also capture cookie headers for session management
        if 'cookie' in request_headers_lower:
            params['headers'].add('cookie')

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

        # Store request example if we have room
        if len(method_data['request_examples']) < config.max_examples_per_endpoint:
            example = {
                'headers': dict(flow.request.headers),
                'timestamp': getattr(flow.request, 'timestamp_start', time.time())
            }

            # Add request body if present
            if flow.request.content:
                try:
                    body_text = flow.request.get_text()
                    if body_text:
                        if content_type and 'json' in content_type:
                            example['body'] = json.loads(body_text)
                        else:
                            example['body'] = body_text
                except:
                    pass

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
        """Export comprehensive API documentation grouped by root domain."""
        from pathlib import Path

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        domains_with_docs = []

        # Generate documentation for each root domain
        for root_domain, root_api_data in self.api_catalog.items():
            if root_api_data['total_calls'] < config.min_calls_per_endpoint:
                continue

            root_domain_dir = output_path / self._sanitize_filename(root_domain)
            root_domain_dir.mkdir(exist_ok=True)

            # Create a combined OpenAPI spec for all domains under this root
            combined_spec = self._generate_combined_openapi_spec(root_domain, root_api_data)

            # Save combined spec
            with open(root_domain_dir / "openapi.json", 'w') as f:
                json.dump(combined_spec, f, indent=2)

            # Generate summary report for the root domain
            self._generate_root_domain_summary_report(root_domain, root_api_data, root_domain_dir)

            # Also generate individual specs for each full domain
            for domain, api_data in root_api_data['domains'].items():
                if api_data['total_calls'] < config.min_calls_per_endpoint:
                    continue

                domain_spec = self._generate_openapi_spec(domain, api_data)
                domain_file = root_domain_dir / f"{self._sanitize_filename(domain)}.json"

                with open(domain_file, 'w') as f:
                    json.dump(domain_spec, f, indent=2)

            domains_with_docs.append({
                'root_domain': root_domain,
                'title': combined_spec['info']['title'],
                'total_calls': root_api_data['total_calls'],
                'domain_count': len(root_api_data['domains']),
                'endpoint_count': sum(len([ep for ep in api_data['endpoints'].values()
                                         if any(m['count'] >= config.min_calls_per_endpoint
                                               for m in ep['methods'].values())])
                                     for api_data in root_api_data['domains'].values())
            })

            logging.info(f"📚 Generated API documentation for {root_domain} in {root_domain_dir}")

        # Generate interactive viewer
        if domains_with_docs:
            self._generate_viewer_html(output_path, domains_with_docs)
            logging.info(f"🚀 Generated interactive viewer: {output_path}/viewer.html")

    def _generate_openapi_spec(self, domain: str, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate OpenAPI 3.0 specification from captured APIs for a specific domain."""
        min_calls = config.min_calls_per_endpoint

        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": f"API Documentation: {domain}",
                "version": "1.0.0",
                "description": "API documentation generated from captured traffic"
            },
            "servers": [{"url": api_data['base_url']}] if api_data['base_url'] else [],
            "components": {
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                        "description": "Bearer token authentication"
                    },
                    "apiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key",
                        "description": "API key authentication"
                    },
                    "cookieAuth": {
                        "type": "apiKey",
                        "in": "cookie",
                        "name": "sessionId",
                        "description": "Cookie-based session authentication"
                    },
                    "csrfAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-CSRF-Token",
                        "description": "CSRF token authentication"
                    },
                    "sessionAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-Session-Token",
                        "description": "Session token authentication"
                    }
                }
            },
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

                # Add security requirements if auth is detected
                auth_headers = params.get('headers', set())
                auth_detected = any(header in auth_headers for header in [
                    'authorization', 'x-api-key', 'x-auth-token', 'x-access-token',
                    'x-csrf-token', 'x-session-token', 'cookie'
                ])

                if auth_detected:
                    method_spec["security"] = []

                    # Bearer token auth
                    if 'authorization' in auth_headers:
                        method_spec["security"].append({"bearerAuth": []})

                    # API key auth
                    if any(header in auth_headers for header in ['x-api-key', 'x-auth-token', 'x-access-token']):
                        method_spec["security"].append({"apiKeyAuth": []})

                    # Cookie auth
                    if 'cookie' in auth_headers:
                        method_spec["security"].append({"cookieAuth": []})

                    # CSRF token auth
                    if 'x-csrf-token' in auth_headers:
                        method_spec["security"].append({"csrfAuth": []})

                    # Session token auth
                    if 'x-session-token' in auth_headers:
                        method_spec["security"].append({"sessionAuth": []})

                # Query parameters with examples
                query_examples = method_data.get('query_examples', {})
                for param in params['query']:
                    param_spec = {
                        "name": param,
                        "in": "query",
                        "schema": {"type": "string"}
                    }
                    # Add example value if available
                    if param in query_examples:
                        param_spec["example"] = query_examples[param]
                    method_spec["parameters"].append(param_spec)

                # Path parameters with examples
                path_examples = method_data.get('path_examples', {})
                for param in params['path']:
                    param_spec = {
                        "name": param,
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"}
                    }
                    # Add example value if available
                    if param in path_examples:
                        param_spec["example"] = path_examples[param]
                    method_spec["parameters"].append(param_spec)

                # Header parameters with examples from captured requests
                if method_data['request_examples']:
                    example_headers = method_data['request_examples'][0].get('headers', {})
                    # Create case-insensitive header lookup
                    example_headers_lower = {k.lower(): v for k, v in example_headers.items()}

                    # Add auth header parameters with actual captured values
                    auth_header_patterns = ['authorization', 'cookie']
                    for header in auth_header_patterns:
                        if header in auth_headers and header in example_headers_lower:
                            param_spec = {
                                "name": header,
                                "in": "header",
                                "required": True,
                                "schema": {"type": "string"},
                                "example": example_headers_lower[header]
                            }

                            # Add description based on header type
                            if header == 'authorization':
                                param_spec["description"] = "Bearer token authentication (captured from MITM)"
                            elif header == 'cookie':
                                param_spec["description"] = "Session cookies (captured from MITM)"

                            method_spec["parameters"].append(param_spec)
                    
                    # Add all x-* headers that were captured
                    for header in auth_headers:
                        if header.startswith('x-') and header in example_headers_lower:
                            param_spec = {
                                "name": header,
                                "in": "header",
                                "required": True,
                                "schema": {"type": "string"},
                                "example": example_headers_lower[header],
                                "description": f"API authentication header (captured from MITM)"
                            }
                            method_spec["parameters"].append(param_spec)

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

    def _generate_combined_openapi_spec(self, root_domain: str, root_api_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate combined OpenAPI spec for all domains under a root domain."""
        min_calls = config.min_calls_per_endpoint

        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": f"API Documentation: {root_domain}",
                "version": "1.0.0",
                "description": f"Combined API documentation for {root_domain} and subdomains"
            },
            "servers": [],
            "components": {
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                        "description": "Bearer token authentication"
                    },
                    "apiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key",
                        "description": "API key authentication"
                    },
                    "cookieAuth": {
                        "type": "apiKey",
                        "in": "cookie",
                        "name": "sessionId",
                        "description": "Cookie-based session authentication"
                    },
                    "csrfAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-CSRF-Token",
                        "description": "CSRF token authentication"
                    },
                    "sessionAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-Session-Token",
                        "description": "Session token authentication"
                    }
                }
            },
            "paths": {}
        }

        # Collect all servers
        servers_seen = set()

        # Process each domain under this root
        for domain, api_data in root_api_data['domains'].items():
            if api_data['total_calls'] < min_calls:
                continue

            # Add server if not already added
            if api_data['base_url'] and api_data['base_url'] not in servers_seen:
                spec["servers"].append({"url": api_data['base_url'], "description": domain})
                servers_seen.add(api_data['base_url'])

            # Process endpoints for this domain
            for path, endpoint_data in api_data['endpoints'].items():
                # Prefix path with domain if multiple domains exist
                display_path = path
                if len(root_api_data['domains']) > 1:
                    display_path = f"[{domain}]{path}"

                path_spec = {}

                for method, method_data in endpoint_data['methods'].items():
                    if method_data['count'] < min_calls:
                        continue

                    # Build method specification
                    method_spec = {
                        "summary": f"{method} {path} ({domain})",
                        "description": f"Captured {method_data['count']} calls from {domain}",
                        "parameters": [],
                        "responses": {}
                    }

                    # Add server selection if multiple servers
                    if len(spec["servers"]) > 1:
                        method_spec["servers"] = [{"url": api_data['base_url']}]

                    # Add security requirements if auth is detected
                    auth_headers = method_data['parameters'].get('headers', set())
                    auth_detected = any(header in auth_headers for header in [
                        'authorization', 'x-api-key', 'x-auth-token', 'x-access-token',
                        'x-csrf-token', 'x-session-token', 'cookie'
                    ])

                    if auth_detected:
                        method_spec["security"] = []

                        # Bearer token auth
                        if 'authorization' in auth_headers:
                            method_spec["security"].append({"bearerAuth": []})

                        # API key auth
                        if any(header in auth_headers for header in ['x-api-key', 'x-auth-token', 'x-access-token']):
                            method_spec["security"].append({"apiKeyAuth": []})

                        # Cookie auth
                        if 'cookie' in auth_headers:
                            method_spec["security"].append({"cookieAuth": []})

                        # CSRF token auth
                        if 'x-csrf-token' in auth_headers:
                            method_spec["security"].append({"csrfAuth": []})

                        # Session token auth
                        if 'x-session-token' in auth_headers:
                            method_spec["security"].append({"sessionAuth": []})

                    # Add parameters
                    params = method_data['parameters']

                    # Query parameters with examples
                    query_examples = method_data.get('query_examples', {})
                    for param in params['query']:
                        param_spec = {
                            "name": param,
                            "in": "query",
                            "schema": {"type": "string"}
                        }
                        # Add example value if available
                        if param in query_examples:
                            param_spec["example"] = query_examples[param]
                        method_spec["parameters"].append(param_spec)

                    # Path parameters with examples
                    path_examples = method_data.get('path_examples', {})
                    for param in params['path']:
                        param_spec = {
                            "name": param,
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"}
                        }
                        # Add example value if available
                        if param in path_examples:
                            param_spec["example"] = path_examples[param]
                        method_spec["parameters"].append(param_spec)

                    # Header parameters with examples from captured requests
                    if method_data['request_examples']:
                        example_headers = method_data['request_examples'][0].get('headers', {})
                        # Create case-insensitive header lookup
                        example_headers_lower = {k.lower(): v for k, v in example_headers.items()}

                        # Add auth header parameters with actual captured values
                        auth_header_patterns = ['authorization', 'cookie']
                        for header in auth_header_patterns:
                            if header in auth_headers and header in example_headers_lower:
                                param_spec = {
                                    "name": header,
                                    "in": "header",
                                    "required": True,
                                    "schema": {"type": "string"},
                                    "example": example_headers_lower[header]
                                }

                                # Add description based on header type
                                if header == 'authorization':
                                    param_spec["description"] = "Bearer token authentication (captured from MITM)"
                                elif header == 'cookie':
                                    param_spec["description"] = "Session cookies (captured from MITM)"

                                method_spec["parameters"].append(param_spec)
                        
                        # Add all x-* headers that were captured
                        for header in auth_headers:
                            if header.startswith('x-') and header in example_headers_lower:
                                param_spec = {
                                    "name": header,
                                    "in": "header", 
                                    "required": True,
                                    "schema": {"type": "string"},
                                    "example": example_headers_lower[header],
                                    "description": f"API authentication header (captured from MITM)"
                                }
                                method_spec["parameters"].append(param_spec)

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
                    spec["paths"][display_path] = path_spec

        return spec

    def _generate_root_domain_summary_report(self, root_domain: str, root_api_data: Dict, output_dir):
        """Generate human-readable summary report for a root domain."""
        # Calculate context statistics for the entire root domain
        context_stats = root_api_data.get('context_stats', {})
        context_summary = []
        for context, count in sorted(context_stats.items()):
            icon = "🌐" if context == "browser" else "⚡" if context == "api" else "❓"
            context_summary.append(f"**{icon} {context.title()}:** {count} calls")

        report = [
            f"# API Documentation: {root_domain}",
            f"",
            f"**Root Domain:** {root_domain}",
            f"**Total API Calls:** {root_api_data['total_calls']}",
            f"**Subdomains Discovered:** {len(root_api_data['domains'])}",
            f"",
            f"## Request Context Distribution",
            f"",
            *context_summary,
            f"",
            f"## Subdomains",
            f""
        ]

        # List all subdomains
        for domain, api_data in sorted(root_api_data['domains'].items()):
            total_calls = api_data['total_calls']
            endpoint_count = len(api_data['endpoints'])

            report.extend([
                f"### {domain}",
                f"",
                f"**Base URL:** {api_data['base_url']}",
                f"**Total Calls:** {total_calls}",
                f"**Endpoints:** {endpoint_count}",
                f""
            ])

            # Show top endpoints for this domain
            if api_data['endpoints']:
                report.append("**Top Endpoints:**")
                endpoint_calls = [(path, sum(m['count'] for m in ep['methods'].values()))
                                for path, ep in api_data['endpoints'].items()]
                top_endpoints = sorted(endpoint_calls, key=lambda x: x[1], reverse=True)[:5]

                for path, calls in top_endpoints:
                    methods = list(api_data['endpoints'][path]['methods'].keys())
                    report.append(f"- `{path}` [{', '.join(methods)}]: {calls} calls")

                report.append("")

        with open(output_dir / "README.md", 'w') as f:
            f.write('\n'.join(report))

    def _generate_summary_report(self, domain: str, api_data: Dict, output_dir):
        """Generate human-readable summary report."""
        # Calculate context statistics
        context_stats = api_data.get('context_stats', {})
        context_summary = []
        for context, count in sorted(context_stats.items()):
            icon = "🌐" if context == "browser" else "⚡" if context == "api" else "❓"
            context_summary.append(f"**{icon} {context.title()}:** {count} calls")

        report = [
            f"# API Documentation: {domain}",
            f"",
            f"**Base URL:** {api_data['base_url']}",
            f"**Total API Calls:** {api_data['total_calls']}",
            f"**Endpoints Discovered:** {len(api_data['endpoints'])}",
            f"",
            f"## Request Context Distribution",
            f"",
            *context_summary,
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
                if method_data['count'] < config.min_calls_per_endpoint:
                    continue

                # Context breakdown for this method
                contexts = method_data.get('contexts', {})
                context_breakdown = []
                for context, count in sorted(contexts.items()):
                    icon = "🌐" if context == "browser" else "⚡" if context == "api" else "❓"
                    context_breakdown.append(f"{icon} {context.title()}: {count}")

                report.extend([
                    f"#### {method} {path}",
                    f"",
                    f"**Calls:** {method_data['count']}",
                    f"**Context:** {', '.join(context_breakdown) if context_breakdown else 'N/A'}",
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

    def _generate_viewer_html(self, output_path, domains_with_docs):
        """Generate interactive HTML viewer for all API documentation using Scalar."""

        viewer_html = f'''<!doctype html>
<html>
<head>
    <title>Scalar API Reference</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
        body {{
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }}
        .header {{
            background: #1f2937;
            color: white;
            padding: 1rem 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 1.25rem;
        }}
        .api-selector {{
            font-size: 0.875rem;
            padding: 0.4rem 0.6rem;
            border-radius: 0.375rem;
            border: 1px solid #ccc;
            min-width: 200px;
        }}
        #app {{
            height: calc(100vh - 80px);
        }}
        .loading {{
            padding: 2rem;
            text-align: center;
            color: #666;
        }}
    </style>
</head>

<body>
    <div class="header">
        <h1>🚀 API Documentation (Grouped by Root Domain)</h1>
        <select class="api-selector" id="apiSelector" onchange="loadAPI()">
            <option value="">Select a root domain to view...</option>
            {chr(10).join(f'<option value="{d["root_domain"]}">{d["title"]} ({d["total_calls"]} calls, {d["domain_count"]} domains)</option>' for d in domains_with_docs)}
        </select>
    </div>

    <div id="app">
        <div class="loading">📚 Select a root domain from the dropdown above to view its API documentation</div>
    </div>

    <!-- Load the Script -->
    <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>

    <!-- Initialize the Scalar API Reference -->
    <script>
        function loadAPI() {{
            const selector = document.getElementById('apiSelector');
            const selectedRootDomain = selector.value;

            if (!selectedRootDomain) {{
                document.getElementById('app').innerHTML =
                    '<div class="loading">📚 Select a root domain from the dropdown above to view its API documentation</div>';
                return;
            }}

            // Sanitize domain name for file path (same logic as _sanitize_filename)
            const sanitizedDomain = selectedRootDomain.replace(/[^\\w\\-_.]/g, '_');
            const specUrl = `./${{sanitizedDomain}}/openapi.json`;

            // Clear the container
            document.getElementById('app').innerHTML = '';

            // Create Scalar API reference
            Scalar.createApiReference('#app', {{
                url: specUrl,
                proxyUrl: 'https://proxy.scalar.com',
                theme: 'default',
                showSidebar: true,
                searchHotKey: 'k',
                metaData: {{
                    title: `API Documentation: ${{selectedRootDomain}}`,
                    description: `Generated API documentation for ${{selectedRootDomain}} and subdomains`
                }}
            }});
        }}

        // Auto-load first API if there's only one
        if (document.querySelectorAll('#apiSelector option').length === 2) {{
            document.getElementById('apiSelector').selectedIndex = 1;
            loadAPI();
        }}
    </script>
</body>
</html>'''

        with open(output_path / "viewer.html", 'w') as f:
            f.write(viewer_html)


# Register the addon
addons = [APIExtractor()]
