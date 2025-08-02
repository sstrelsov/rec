#!/usr/bin/env python3
"""
parser.py - Unified mitmproxy dump parser

Consolidates parsing functionality with both simple and advanced capabilities.
"""

import subprocess
import os
import json
from typing import List, Dict, Any, Optional
from addons.context_detector import detect_request_context, RequestContext


class FlowParser:
    """Unified parser for mitmproxy dump files."""

    def __init__(self):
        self.mitmdump_timeout = 120

    def parse_flows(self, dump_file: str) -> List[Dict[str, Any]]:
        """Parse mitmproxy dump file directly using Python API."""
        if not os.path.exists(dump_file):
            print(f"❌ Dump file not found: {dump_file}")
            return []

        try:
            from mitmproxy import io, http
            from mitmproxy.exceptions import FlowReadException

            flows = []

            with open(dump_file, "rb") as f:
                freader = io.FlowReader(f)
                try:
                    for flow_data in freader.stream():
                        if isinstance(flow_data, http.HTTPFlow):
                            flow_dict = self._extract_flow_data(flow_data)
                            if flow_dict:
                                flows.append(flow_dict)

                except FlowReadException as e:
                    print(f"⚠️  Warning: Error reading some flows: {e}")
                    # Continue with flows we could read

            return flows

        except ImportError:
            print("❌ mitmproxy not installed. Install with: pip install mitmproxy")
            return []
        except Exception as e:
            print(f"❌ Error parsing dump file: {e}")
            return []

    def _extract_response_content(self, response) -> Optional[str]:
        """Extract response content with robust encoding handling."""
        if not response or not hasattr(response, 'content'):
            return ""

        if not response.content:
            return ""  # Return empty string instead of None for responses with no content

        # Try to get raw content first
        try:
            # Just get the raw content bytes and decode as UTF-8
            content_bytes = response.content
            if content_bytes:
                # Try UTF-8 first, fall back to latin1 which never fails
                try:
                    return content_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    return content_bytes.decode('latin1')
            else:
                return ""
        except Exception:
            # If all else fails, try mitmproxy's built-in method
            try:
                text_content = response.get_text()
                return text_content if text_content is not None else ""
            except Exception:
                # Last resort - indicate we have content but can't decode it
                if hasattr(response, 'content') and response.content:
                    return f"<binary: {len(response.content)} bytes>"
                return ""

    def _extract_flow_data(self, flow) -> Optional[Dict[str, Any]]:
        """Extract data from a single flow object."""
        if not hasattr(flow, 'request'):
            return None

        try:
            # Get request content
            req_content = None
            if flow.request and flow.request.content:
                try:
                    req_content = flow.request.get_text()
                except:
                    req_content = f"<binary: {len(flow.request.content)} bytes>"

            # Get response content with better encoding handling
            resp_content = None
            status_code = None
            response_headers = {}
            response_size = 0

            if flow.response:
                status_code = getattr(flow.response, 'status_code', None)
                response_headers = dict(getattr(flow.response, 'headers', {}))

                if flow.response.content:
                    resp_content = self._extract_response_content(flow.response)
                    response_size = len(flow.response.content)
                else:
                    resp_content = ""  # Empty response

            # Detect request context
            context = detect_request_context(flow)

            return {
                "timestamp": getattr(flow.request, 'timestamp_start', 0),
                "method": getattr(flow.request, 'method', 'UNKNOWN'),
                "url": getattr(flow.request, 'pretty_url', 'unknown'),
                "host": getattr(flow.request, 'pretty_host', 'unknown'),
                "path": getattr(flow.request, 'path', '/'),
                "request_headers": dict(getattr(flow.request, 'headers', {})),
                "request_content": req_content,
                "status_code": status_code,
                "response_headers": response_headers,
                "response_content": resp_content,
                "response_size": response_size,
                "context": context.value,
                "context_type": context.value  # For backward compatibility
            }

        except Exception as e:
            # Return basic error info - don't completely drop the flow
            return {
                "error": f"Parse failed: {e}",
                "method": getattr(flow.request, 'method', 'UNKNOWN') if hasattr(flow, 'request') else 'UNKNOWN',
                "url": getattr(flow.request, 'pretty_url', 'unknown') if hasattr(flow, 'request') else 'unknown',
                "status_code": getattr(flow.response, 'status_code', None) if hasattr(flow, 'response') and flow.response else None
            }

    def simple_view(self, dump_file: str, filter_domain: str = None) -> None:
        """Quick view using mitmdump's built-in formatting."""
        if not os.path.exists(dump_file):
            print(f"❌ Dump file not found: {dump_file}")
            return

        print(f"📖 Reading traffic dump: {dump_file}")

        try:
            cmd = ["mitmdump", "-r", dump_file, "-q"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                flow_count = 0
                matching_flows = 0

                print(f"📊 Found {len([l for l in lines if l.strip()])} HTTP flows")

                if filter_domain:
                    print(f"🔍 Filtering by domain: {filter_domain}")

                print("\n🌐 Traffic Summary:")

                for line in lines:
                    if line.strip():
                        flow_count += 1
                        if filter_domain:
                            if filter_domain.lower() in line.lower():
                                matching_flows += 1
                                print(f"🔗 Flow #{matching_flows}: {line}")
                        else:
                            if flow_count <= 20:  # Show first 20 flows
                                print(f"🔗 Flow #{flow_count}: {line}")

                if filter_domain:
                    print(f"\n📊 Found {matching_flows} flows matching '{filter_domain}'")
                elif flow_count > 20:
                    print(f"\n... and {flow_count - 20} more flows")

            else:
                print(f"❌ Error: {result.stderr}")

        except subprocess.TimeoutExpired:
            print("❌ Parsing timed out")
        except FileNotFoundError:
            print("❌ mitmdump not found. Install with: brew install mitmproxy")
        except Exception as e:
            print(f"❌ Error: {e}")

    def filter_flows(self, flows: List[Dict[str, Any]],
                    domain_filter: Optional[str] = None,
                    method_filter: Optional[str] = None,
                    status_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """Filter flows based on various criteria."""
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

    def group_by_domain(self, flows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group flows by domain."""
        domains = {}
        for flow in flows:
            domain = flow.get('host', 'unknown')
            if domain not in domains:
                domains[domain] = []
            domains[domain].append(flow)
        return domains

    def get_summary(self, flows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary statistics for flows."""
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
            domain = flow.get('host', 'unknown')
            domains[domain] = domains.get(domain, 0) + 1

            method = flow.get('method', 'UNKNOWN')
            methods[method] = methods.get(method, 0) + 1

            status = flow.get('status_code')
            if status:
                status_codes[status] = status_codes.get(status, 0) + 1

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

