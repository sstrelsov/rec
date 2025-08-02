#!/usr/bin/env python3
"""
traffic_viewer.py - Traffic Analysis and Viewing

Provides functionality to view and analyze captured network traffic.
"""

import json
import time
from typing import List, Dict, Any, Optional
from dump_parser import DumpParser


class TrafficViewer:
    """Views and analyzes captured network traffic."""

    def __init__(self):
        self.parser = DumpParser()

    def view_capture(self, dump_file: str,
                    filter_domain: Optional[str] = None,
                    max_flows: int = 20) -> None:
        """View and analyze captured traffic.

        Args:
            dump_file: Path to the dump file to analyze.
            filter_domain: Optional domain filter.
            max_flows: Maximum number of flows to display in detail.
        """
        print(f"📖 Reading traffic dump: {dump_file}")

        flows = self.parser.parse_mitm_dump(dump_file)

        if not flows:
            print("❌ No flows found or error parsing dump file")
            return

        # Filter by domain if specified
        if filter_domain:
            flows = self.parser.filter_flows(flows, domain_filter=filter_domain)
            print(f"🔍 Filtered to {len(flows)} flows matching '{filter_domain}'")

        print(f"\n📊 Found {len(flows)} HTTP flows\n")

        # Show summary
        self._display_summary(flows)

        # Display detailed flows
        self._display_detailed_flows(flows, max_flows)

    def _display_summary(self, flows: List[Dict[str, Any]]) -> None:
        """Display summary information about flows."""
        summary = self.parser.get_flow_summary(flows)

        # Display domain summary
        print("🌐 Domains captured:")
        for domain, count in sorted(summary["domains"].items(),
                                   key=lambda x: x[1], reverse=True):
            print(f"  • {domain}: {count} requests")
        print()

        # Display method summary
        if summary["methods"]:
            print("📋 HTTP Methods:")
            for method, count in sorted(summary["methods"].items()):
                print(f"  • {method}: {count} requests")
            print()

        # Display status code summary
        if summary["status_codes"]:
            print("📊 Status Codes:")
            for status, count in sorted(summary["status_codes"].items()):
                status_emoji = self._get_status_emoji(status)
                print(f"  • {status} {status_emoji}: {count} responses")
            print()

        # Display size and timing info
        total_size_mb = summary["total_size"] / (1024 * 1024)
        print(f"📈 Total Response Size: {total_size_mb:.2f} MB")

        if summary["time_range"]["start"] and summary["time_range"]["end"]:
            start_time = time.strftime('%H:%M:%S', time.localtime(summary["time_range"]["start"]))
            end_time = time.strftime('%H:%M:%S', time.localtime(summary["time_range"]["end"]))
            duration = summary["time_range"]["end"] - summary["time_range"]["start"]
            print(f"⏰ Time Range: {start_time} - {end_time} ({duration:.1f}s)")

        print()

    def _display_detailed_flows(self, flows: List[Dict[str, Any]], max_flows: int) -> None:
        """Display detailed information about individual flows."""
        for i, flow in enumerate(flows, 1):
            print(f"🔗 Flow #{i}")
            print(f"   Method: {flow.get('method', 'N/A')}")
            print(f"   URL: {flow.get('url', 'N/A')}")

            status_code = flow.get('status_code', 'N/A')
            status_emoji = self._get_status_emoji(status_code) if status_code != 'N/A' else ''
            print(f"   Status: {status_code} {status_emoji}")

            response_size = flow.get('response_size', 0)
            size_formatted = self._format_size(response_size)
            print(f"   Size: {size_formatted}")

            # Show content type
            headers = flow.get('response_headers', {})
            content_type = headers.get('content-type', headers.get('Content-Type', 'N/A'))
            print(f"   Content-Type: {content_type}")

            # Show JSON preview for API responses
            if 'json' in content_type.lower():
                self._display_json_preview(flow)

            # Show timing
            timestamp = flow.get('timestamp', 0)
            if timestamp:
                time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
                print(f"   Timestamp: {time_str}")

            print()

            # Stop after max_flows to avoid overwhelming output
            if i >= max_flows:
                remaining = len(flows) - i
                if remaining > 0:
                    print(f"... and {remaining} more flows")
                break

    def _display_json_preview(self, flow: Dict[str, Any]) -> None:
        """Display a preview of JSON response content."""
        response_content = flow.get('response_content')
        if response_content:
            try:
                json_data = json.loads(response_content)
                preview = json.dumps(json_data, indent=2)[:300]
                if len(preview) == 300:
                    preview += "..."
                print(f"   JSON Preview:")
                for line in preview.split('\n'):
                    print(f"     {line}")
            except (json.JSONDecodeError, TypeError):
                # Not valid JSON or too large
                preview = str(response_content)[:100]
                if len(response_content) > 100:
                    preview += "..."
                print(f"   Content Preview: {preview}")

    def _get_status_emoji(self, status_code) -> str:
        """Get emoji representation for HTTP status codes."""
        try:
            code = int(status_code)
            if 200 <= code < 300:
                return "✅"
            elif 300 <= code < 400:
                return "🔄"
            elif 400 <= code < 500:
                return "❌"
            elif 500 <= code < 600:
                return "💥"
            else:
                return "❓"
        except (ValueError, TypeError):
            return "❓"

    def _format_size(self, size_bytes: int) -> str:
        """Format byte size in human-readable format."""
        if size_bytes == 0:
            return "0 B"

        units = ['B', 'KB', 'MB', 'GB']
        size = float(size_bytes)
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"

    def export_flows_to_json(self, flows: List[Dict[str, Any]], output_file: str) -> bool:
        """Export flows to JSON file.

        Args:
            flows: List of flow dictionaries.
            output_file: Path to output JSON file.

        Returns:
            True if export was successful, False otherwise.
        """
        try:
            with open(output_file, 'w') as f:
                json.dump(flows, f, indent=2, default=str)
            print(f"✅ Exported {len(flows)} flows to: {output_file}")
            return True
        except Exception as e:
            print(f"❌ Error exporting to JSON: {e}")
            return False

    def search_flows(self, flows: List[Dict[str, Any]],
                    search_term: str,
                    search_in: List[str] = None) -> List[Dict[str, Any]]:
        """Search for flows containing a specific term.

        Args:
            flows: List of flow dictionaries.
            search_term: Term to search for.
            search_in: List of fields to search in. Default searches common fields.

        Returns:
            List of matching flows.
        """
        if search_in is None:
            search_in = ['url', 'path', 'request_content', 'response_content']

        search_term_lower = search_term.lower()
        matching_flows = []

        for flow in flows:
            for field in search_in:
                field_value = flow.get(field, '')
                if isinstance(field_value, str) and search_term_lower in field_value.lower():
                    matching_flows.append(flow)
                    break

        return matching_flows
