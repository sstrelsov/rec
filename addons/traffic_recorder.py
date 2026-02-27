#!/usr/bin/env python3
"""
traffic_recorder.py - Network Traffic Recorder

Records individual network calls in a chronological directory structure
organized by base domain with metadata, auth tokens, and HTTPie scripts.
"""

import json
import re
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, parse_qs
from mitmproxy import http
import sys

# Add parent directory to path to find config module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from domain_utils import extract_root_domain, matches_target_domains


class TrafficRecorder:
    """Records individual network traffic calls in chronological structure."""

    def __init__(self):
        # Track sequence numbers per domain
        self.domain_sequences = {}
        # Track metadata per domain
        self.domain_metadata = {}

    def done(self):
        """Called when mitmproxy shuts down - export metadata."""
        self.export_metadata()

    def response(self, flow: http.HTTPFlow):
        """Process completed requests and record them."""
        # Skip traffic not matching target domains
        if not matches_target_domains(flow.request.pretty_host, config.target_domains):
            return

        # Skip ads/analytics traffic first
        if self._is_blocked_traffic(flow):
            return

        # Apply configurable noise filtering
        if self._is_filtered_noise(flow):
            return

        # Skip if no response
        if not flow.response:
            return

        try:
            self._record_traffic(flow)
        except Exception as e:
            print(f"⚠️  Traffic recording failed for {flow.request.pretty_url}: {e}")

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

    def _is_filtered_noise(self, flow: http.HTTPFlow) -> bool:
        """Check if request should be filtered as noise based on config."""
        method = flow.request.method.upper()
        path = flow.request.path.lower()

        # Check HTTP method filtering
        if method not in config.http_methods:
            return True

        # Static assets filtering
        if config.filter_static_assets:
            static_extensions = ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', 
                               '.woff', '.woff2', '.ttf', '.eot', '.otf', '.map']
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

        # Prefetch requests filtering
        if config.filter_prefetch_requests:
            purpose_header = flow.request.headers.get('purpose', '').lower()
            if 'prefetch' in purpose_header:
                return True

        return False

    def _record_traffic(self, flow: http.HTTPFlow):
        """Record traffic call in chronological directory structure."""
        parsed_url = urlparse(flow.request.pretty_url)
        domain = parsed_url.netloc
        root_domain = extract_root_domain(domain)
        
        # Get sequence number for this domain
        if root_domain not in self.domain_sequences:
            self.domain_sequences[root_domain] = 0
        self.domain_sequences[root_domain] += 1
        sequence = self.domain_sequences[root_domain]

        # Generate directory name
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        endpoint_name = self._extract_endpoint_name(flow.request.method, parsed_url.path)
        dir_name = f"{flow.request.method.lower()}_{endpoint_name}_{timestamp}_{sequence:03d}"

        # Create directory structure
        output_dir = Path(config.output_dir) / root_domain / dir_name
        output_dir.mkdir(parents=True, exist_ok=True)

        # Extract auth info
        auth_token = self._extract_auth_token(flow)
        
        # Generate files
        self._write_auth_file(output_dir, auth_token)
        self._write_request_json(output_dir, flow, auth_token is not None)
        self._write_response_file(output_dir, flow)
        
        # Update domain metadata
        self._update_metadata(root_domain, domain, flow, auth_token)

    def _extract_endpoint_name(self, method: str, path: str) -> str:
        """Extract a clean endpoint name from the path."""
        # Remove query parameters
        clean_path = path.split('?')[0]
        
        # Remove leading/trailing slashes
        clean_path = clean_path.strip('/')
        
        # Split into parts and take meaningful segments
        parts = [p for p in clean_path.split('/') if p]
        
        # If empty, use root
        if not parts:
            return "root"
        
        # Take up to 3 meaningful parts, skip version identifiers at start
        meaningful_parts = []
        for part in parts:
            # Skip version patterns like v1, v2, api
            if re.match(r'^(api|v\d+)$', part.lower()):
                continue
            # Replace IDs with generic terms
            if re.match(r'^\d+$', part):
                part = "id"
            elif re.match(r'^[a-f0-9-]{36}$', part):
                part = "uuid"
            elif re.match(r'^[a-f0-9]{24}$', part):
                part = "objectid"
            elif len(part) > 20:
                part = "token"
            
            meaningful_parts.append(part)
            if len(meaningful_parts) >= 3:
                break
        
        if not meaningful_parts:
            return "endpoint"
        
        # Join with underscores and sanitize
        name = "_".join(meaningful_parts)
        name = re.sub(r'[^\w_]', '_', name)
        name = re.sub(r'_+', '_', name)  # Remove duplicate underscores
        return name.lower()

    def _extract_auth_token(self, flow: http.HTTPFlow) -> Optional[str]:
        """Extract authentication token from request."""
        # Check Authorization header
        auth_header = flow.request.headers.get('authorization', '')
        if auth_header:
            # Extract Bearer token
            if auth_header.startswith('Bearer '):
                return auth_header[7:]
            elif auth_header.startswith('Basic '):
                return auth_header[6:]
            else:
                return auth_header
        
        # Check for API key headers
        api_key_headers = ['x-api-key', 'x-auth-token', 'x-access-token', 'apikey']
        for header in api_key_headers:
            value = flow.request.headers.get(header, '')
            if value:
                return value
        
        # Check for session tokens in cookies
        cookie_header = flow.request.headers.get('cookie', '')
        if cookie_header:
            # Look for session-like cookies
            session_patterns = [r'session[^=]*=([^;]+)', r'auth[^=]*=([^;]+)', r'token[^=]*=([^;]+)']
            for pattern in session_patterns:
                match = re.search(pattern, cookie_header, re.IGNORECASE)
                if match:
                    return match.group(1)
        
        return None

    def _write_auth_file(self, output_dir: Path, auth_token: Optional[str]):
        """Write auth.txt file with authentication token."""
        auth_file = output_dir / "auth.txt"
        if auth_token:
            with open(auth_file, 'w') as f:
                f.write(auth_token)
        else:
            # Create empty file to maintain structure
            auth_file.touch()

    def _write_request_json(self, output_dir: Path, flow: http.HTTPFlow, has_auth: bool):
        """Write request as JSON for easy reproduction."""
        request_file = output_dir / "request.json"
        
        # Build headers dictionary
        headers = {}
        for name, value in flow.request.headers.items():
            # Skip problematic headers
            if name.lower() in ['host', 'content-length', 'connection']:
                continue
            
            # Handle auth headers specially
            if name.lower() == 'authorization' and has_auth:
                if value.startswith('Bearer '):
                    headers[name] = "Bearer {{auth_token}}"
                elif value.startswith('Basic '):
                    headers[name] = "Basic {{auth_token}}"
                else:
                    headers[name] = "{{auth_token}}"
            elif name.lower() in ['x-api-key', 'x-auth-token', 'x-access-token', 'apikey'] and has_auth:
                headers[name] = "{{auth_token}}"
            else:
                headers[name] = value
        
        # Build request object
        parsed_url = urlparse(flow.request.pretty_url)
        request_data = {
            "method": flow.request.method,
            "url": flow.request.pretty_url,
            "headers": headers
        }
        
        # Add request body if present
        if flow.request.content and flow.request.method in ['POST', 'PUT', 'PATCH']:
            try:
                content_type = flow.request.headers.get('content-type', '').lower()
                if 'json' in content_type:
                    body_text = flow.request.get_text()
                    if body_text:
                        # Parse and include JSON body
                        body_data = json.loads(body_text)
                        request_data["body"] = body_data
                else:
                    # Non-JSON body
                    body_text = flow.request.get_text()
                    if body_text:
                        request_data["body"] = body_text
            except Exception as e:
                request_data["body_error"] = f"Could not parse request body: {e}"
        
        # Add metadata comments
        request_data["_metadata"] = {
            "original_url": flow.request.pretty_url,
            "method": flow.request.method,
            "status": flow.response.status_code if flow.response else None,
            "captured_at": datetime.now().isoformat(),
            "auth_required": has_auth,
            "instructions": {
                "auth_token": "Replace {{auth_token}} with actual token from auth.txt",
                "usage": "Use this JSON with curl, httpie, or any HTTP client"
            }
        }
        
        with open(request_file, 'w') as f:
            json.dump(request_data, f, indent=2, ensure_ascii=False)

    def _write_response_file(self, output_dir: Path, flow: http.HTTPFlow):
        """Write response file in appropriate format."""
        if not flow.response:
            return
        
        content_type = flow.response.headers.get('content-type', '').lower()
        
        if 'json' in content_type:
            response_file = output_dir / "response.json"
            try:
                response_text = flow.response.get_text()
                if response_text:
                    # Parse and pretty-print JSON
                    response_data = json.loads(response_text)
                    with open(response_file, 'w') as f:
                        json.dump(response_data, f, indent=2, ensure_ascii=False)
                else:
                    response_file.touch()
            except Exception as e:
                # Fallback to raw text if JSON parsing fails
                response_file = output_dir / "response.txt"
                with open(response_file, 'w') as f:
                    f.write(f"# JSON parsing failed: {e}\n")
                    f.write(flow.response.get_text() or "")
        elif 'xml' in content_type:
            response_file = output_dir / "response.xml"
            with open(response_file, 'w') as f:
                f.write(flow.response.get_text() or "")
        elif 'html' in content_type:
            response_file = output_dir / "response.html"
            with open(response_file, 'w') as f:
                f.write(flow.response.get_text() or "")
        else:
            # Default to .txt for other content types
            response_file = output_dir / "response.txt"
            with open(response_file, 'w') as f:
                f.write(flow.response.get_text() or "")

    def _update_metadata(self, root_domain: str, full_domain: str, flow: http.HTTPFlow, auth_token: Optional[str]):
        """Update metadata.json for the domain."""
        if root_domain not in self.domain_metadata:
            self.domain_metadata[root_domain] = {
                "base_domain": root_domain,
                "subdomains": set(),
                "endpoints": {},
                "auth": {
                    "type": None,
                    "encoding": None,
                    "expires_at": None,
                    "last_seen": None
                },
                "headers": {
                    "common": {}
                },
                "stats": {
                    "total_calls": 0,
                    "methods": {},
                    "status_codes": {}
                }
            }
        
        metadata = self.domain_metadata[root_domain]
        metadata["subdomains"].add(full_domain)
        metadata["stats"]["total_calls"] += 1
        
        # Update method stats
        request_method = flow.request.method
        if request_method not in metadata["stats"]["methods"]:
            metadata["stats"]["methods"][request_method] = 0
        metadata["stats"]["methods"][request_method] += 1
        
        # Update status code stats
        if flow.response:
            status = flow.response.status_code
            if status not in metadata["stats"]["status_codes"]:
                metadata["stats"]["status_codes"][status] = 0
            metadata["stats"]["status_codes"][status] += 1
        
        # Update endpoint info
        parsed_url = urlparse(flow.request.pretty_url)
        endpoint_key = f"{full_domain}{parsed_url.path}"
        if endpoint_key not in metadata["endpoints"]:
            metadata["endpoints"][endpoint_key] = {
                "methods": [],
                "auth_required": False,
                "content_type": None,
                "examples_count": 0
            }
        
        endpoint = metadata["endpoints"][endpoint_key]
        if request_method not in endpoint["methods"]:
            endpoint["methods"].append(request_method)
        endpoint["examples_count"] += 1
        
        # Update auth info
        if auth_token:
            endpoint["auth_required"] = True
            metadata["auth"]["last_seen"] = datetime.now().isoformat()
            
            # Detect auth type
            auth_header = flow.request.headers.get('authorization', '')
            if auth_header.startswith('Bearer '):
                metadata["auth"]["type"] = "bearer"
                # Try to detect JWT
                if '.' in auth_token and len(auth_token.split('.')) == 3:
                    metadata["auth"]["encoding"] = "jwt"
            elif auth_header.startswith('Basic '):
                metadata["auth"]["type"] = "basic"
                metadata["auth"]["encoding"] = "base64"
            elif flow.request.headers.get('x-api-key'):
                metadata["auth"]["type"] = "api_key"
        
        # Update common headers
        common_headers = metadata["headers"]["common"]
        for name, value in flow.request.headers.items():
            if name.lower() in ['user-agent', 'accept', 'accept-language', 'accept-encoding']:
                common_headers[name] = value
        
        # Update content type
        if flow.request.content:
            content_type = flow.request.headers.get('content-type', '')
            if content_type and not endpoint["content_type"]:
                endpoint["content_type"] = content_type

    def export_metadata(self):
        """Export metadata.json files for each domain."""
        for root_domain, metadata in self.domain_metadata.items():
            domain_dir = Path(config.output_dir) / root_domain
            domain_dir.mkdir(parents=True, exist_ok=True)
            
            # Convert sets to lists for JSON serialization
            metadata_copy = metadata.copy()
            metadata_copy["subdomains"] = sorted(list(metadata["subdomains"]))
            
            metadata_file = domain_dir / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata_copy, f, indent=2, ensure_ascii=False)


# Register the addon
addons = [TrafficRecorder()]