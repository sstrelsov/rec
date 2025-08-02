#!/usr/bin/env python3
"""
generate_reports.py - Generate Enhanced Reports from Existing Captures

Run this on your existing .mitm files to get the API documentation and timeline
without having to recapture everything.
"""

import sys
import argparse
from pathlib import Path

# Import our addons
from addons.api_extractor import APIExtractor
from addons.api_timeline import APITimeline
from parser import FlowParser


def generate_reports_from_file(dump_file: str, output_dir: str = None):
    """Generate enhanced reports from a captured dump file."""

    if not Path(dump_file).exists():
        print(f"❌ File not found: {dump_file}")
        return False

    print(f"📖 Processing capture file: {dump_file}")

    # Parse flows from dump file
    parser = FlowParser()
    flows = parser.parse_flows(dump_file)

    if not flows:
        print("❌ No flows found in dump file")
        return False

    print(f"📊 Found {len(flows)} flows, generating reports...")

    # Initialize addons
    api_extractor = APIExtractor()
    timeline_generator = APITimeline()

    # Process each flow through the addons
    processed_count = 0
    api_count = 0
    timeline_count = 0

    for flow_data in flows:
        # Create a mock flow object for the addons
        mock_flow = create_mock_flow(flow_data)

        if mock_flow:
            processed_count += 1

            # Process through API extractor
            try:
                # Skip ads/analytics
                if not api_extractor._is_blocked_traffic(mock_flow):
                    if api_extractor._is_api_request(mock_flow):
                        api_extractor._extract_api_info(mock_flow)
                        api_count += 1
            except Exception as e:
                print(f"⚠️  API extraction error: {e}")

            # Process through timeline generator
            try:
                if not timeline_generator._is_blocked_traffic(mock_flow):
                    if timeline_generator._is_api_traffic(mock_flow):
                        timeline_generator._record_api_call(mock_flow)
                        timeline_count += 1
            except Exception as e:
                print(f"⚠️  Timeline generation error: {e}")

    print(f"✅ Processed {processed_count} flows")
    print(f"📚 Found {api_count} API calls")
    print(f"🕒 Recorded {timeline_count} timeline entries")

    # Generate reports
    success = True

    try:
        # Generate API documentation
        if api_extractor.api_catalog:
            api_extractor.export_documentation("api_docs")
            print("📚 API documentation generated: api_docs/")
        else:
            print("⚠️  No API calls found for documentation")
    except Exception as e:
        print(f"❌ API documentation generation failed: {e}")
        success = False

    try:
        # Generate timeline
        if timeline_generator.api_calls:
            timeline_generator.generate_timeline_files("api_timeline")
            print("🕒 Timeline generated: api_timeline/timeline.html")
        else:
            print("⚠️  No API calls found for timeline")
    except Exception as e:
        print(f"❌ Timeline generation failed: {e}")
        success = False

    return success


def create_mock_flow(flow_data: dict):
    """Create a mock flow object from parsed flow data."""
    try:
        # Create mock request object
        class MockRequest:
            def __init__(self, data):
                self.method = data.get('method', 'GET')
                self.pretty_url = data.get('url', '')
                self.pretty_host = data.get('host', '')
                self.path = data.get('path', '/')
                self.headers = data.get('request_headers', {})
                self.content = data.get('request_content', '').encode() if data.get('request_content') else b''
                self.timestamp_start = data.get('timestamp', 0)

            def get_text(self):
                return self.content.decode('utf-8', errors='ignore') if self.content else ""

        # Create mock response object
        class MockResponse:
            def __init__(self, data):
                self.status_code = data.get('status_code')
                self.headers = data.get('response_headers', {})
                self.content = data.get('response_content', '').encode() if data.get('response_content') else b''
                self.timestamp_start = data.get('timestamp', 0) + 0.1  # Slight delay

            def get_text(self):
                return self.content.decode('utf-8', errors='ignore') if self.content else ""

        # Create mock flow object
        class MockFlow:
            def __init__(self, data):
                self.request = MockRequest(data)
                self.response = MockResponse(data) if data.get('status_code') else None

        return MockFlow(flow_data)

    except Exception as e:
        print(f"⚠️  Could not create mock flow: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Generate enhanced reports from existing capture files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_reports.py capture.mitm
  python generate_reports.py my_api_session.mitm

This will create:
  api_docs/          # OpenAPI documentation
  api_timeline/      # Interactive timeline
"""
    )

    parser.add_argument('dump_file', help='Path to the .mitm capture file')
    parser.add_argument('--output', '-o', help='Output directory (optional)')

    args = parser.parse_args()

    if not args.dump_file:
        print("❌ Please specify a dump file")
        sys.exit(1)

    print("🚀 Generating enhanced reports from existing capture...")
    success = generate_reports_from_file(args.dump_file, args.output)

    if success:
        print("✨ Reports generated successfully!")
        print("💡 Open api_timeline/timeline.html in your browser")
    else:
        print("❌ Some errors occurred during report generation")
        sys.exit(1)


if __name__ == "__main__":
    main()
