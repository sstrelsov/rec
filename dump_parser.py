#!/usr/bin/env python3
"""
dump_parser.py - mitmproxy Dump File Parser

Handles parsing mitmproxy dump files and extracting flow data.
"""

import subprocess
import tempfile
import os
import json
import time
from typing import List, Dict, Any, Optional


class DumpParser:
    """Parses mitmproxy dump files and extracts flow data."""

    def parse_mitm_dump(self, dump_file: str) -> List[Dict[str, Any]]:
        """Parse mitmproxy dump file and extract flow data.

        Args:
            dump_file: Path to the mitmproxy dump file.

        Returns:
            List of dictionaries containing flow data.
        """
        if not os.path.exists(dump_file):
            print(f"❌ Dump file not found: {dump_file}")
            return []

        try:
            # Create a script to extract JSON data from flows
            script_content = self._create_extraction_script()

            # Write script to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script_content)
                script_path = f.name

            try:
                # Run mitmdump with the extraction script
                cmd = ["mitmdump", "-s", script_path, "-r", dump_file]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

                if result.returncode != 0:
                    print(f"❌ Error parsing dump: {result.stderr}")
                    return []

                # Parse the JSON output
                flows = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            flows.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

                return flows

            finally:
                # Clean up temp file
                try:
                    os.unlink(script_path)
                except:
                    pass

        except subprocess.TimeoutExpired:
            print("❌ Parsing timed out")
            return []
        except Exception as e:
            print(f"❌ Error parsing dump file: {e}")
            return []

    def _create_extraction_script(self) -> str:
        """Create the mitmproxy script for extracting flow data."""
        return '''
import json
from mitmproxy import http

def response(flow: http.HTTPFlow) -> None:
    """Extract flow data and output as JSON."""
    # Skip non-HTTP flows
    if not hasattr(flow, 'request') or not hasattr(flow, 'response'):
        return

    # Skip if no response
    if not flow.response:
        return

    try:
        # Extract request content
        request_content = None
        if flow.request.content:
            try:
                request_content = flow.request.get_text()
            except:
                request_content = f"<binary data: {len(flow.request.content)} bytes>"

        # Extract response content
        response_content = None
        if flow.response.content:
            try:
                response_content = flow.response.get_text()
            except:
                response_content = f"<binary data: {len(flow.response.content)} bytes>"

        flow_data = {
            "timestamp": flow.request.timestamp_start,
            "method": flow.request.method,
            "url": flow.request.pretty_url,
            "host": flow.request.pretty_host,
            "path": flow.request.path,
            "request_headers": dict(flow.request.headers),
            "request_content": request_content,
            "status_code": flow.response.status_code,
            "response_headers": dict(flow.response.headers),
            "response_content": response_content,
            "response_size": len(flow.response.content) if flow.response.content else 0
        }

        print(json.dumps(flow_data))

    except Exception as e:
        # Log error but continue processing
        error_data = {
            "timestamp": getattr(flow.request, 'timestamp_start', 0),
            "method": getattr(flow.request, 'method', 'UNKNOWN'),
            "url": getattr(flow.request, 'pretty_url', 'unknown'),
            "host": getattr(flow.request, 'pretty_host', 'unknown'),
            "path": getattr(flow.request, 'path', '/'),
            "error": f"Failed to parse flow: {e}",
            "request_headers": {},
            "request_content": None,
            "status_code": None,
            "response_headers": {},
            "response_content": None,
            "response_size": 0
        }
        print(json.dumps(error_data))
'''

    def filter_flows(self, flows: List[Dict[str, Any]],
                    domain_filter: Optional[str] = None,
                    method_filter: Optional[str] = None,
                    status_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """Filter flows based on various criteria.

        Args:
            flows: List of flow dictionaries.
            domain_filter: Filter by domain name (case-insensitive).
            method_filter: Filter by HTTP method.
            status_filter: Filter by HTTP status code.

        Returns:
            Filtered list of flows.
        """
        filtered_flows = flows

        if domain_filter:
            filtered_flows = [
                f for f in filtered_flows
                if domain_filter.lower() in f.get('host', '').lower()
            ]

        if method_filter:
            filtered_flows = [
                f for f in filtered_flows
                if f.get('method', '').upper() == method_filter.upper()
            ]

        if status_filter:
            filtered_flows = [
                f for f in filtered_flows
                if f.get('status_code') == status_filter
            ]

        return filtered_flows

    def group_flows_by_domain(self, flows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group flows by domain.

        Args:
            flows: List of flow dictionaries.

        Returns:
            Dictionary mapping domain names to lists of flows.
        """
        domains = {}
        for flow in flows:
            domain = flow.get('host', 'unknown')
            if domain not in domains:
                domains[domain] = []
            domains[domain].append(flow)
        return domains

    def get_flow_summary(self, flows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary statistics for a list of flows.

        Args:
            flows: List of flow dictionaries.

        Returns:
            Dictionary containing summary statistics.
        """
        if not flows:
            return {
                "total_flows": 0,
                "domains": {},
                "methods": {},
                "status_codes": {},
                "total_size": 0
            }

        domains = {}
        methods = {}
        status_codes = {}
        total_size = 0

        for flow in flows:
            # Count domains
            domain = flow.get('host', 'unknown')
            domains[domain] = domains.get(domain, 0) + 1

            # Count methods
            method = flow.get('method', 'UNKNOWN')
            methods[method] = methods.get(method, 0) + 1

            # Count status codes
            status = flow.get('status_code')
            if status:
                status_codes[status] = status_codes.get(status, 0) + 1

            # Sum response sizes
            total_size += flow.get('response_size', 0)

        return {
            "total_flows": len(flows),
            "domains": domains,
            "methods": methods,
            "status_codes": status_codes,
            "total_size": total_size,
            "time_range": {
                "start": min(flow.get('timestamp', 0) for flow in flows),
                "end": max(flow.get('timestamp', 0) for flow in flows)
            }
        }
