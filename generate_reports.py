#!/usr/bin/env python3
"""
Enhanced Report Generator for MITM Capture Files

Generates comprehensive API documentation and timeline visualizations
from captured mitmproxy dump files.

Usage:
    python generate_reports.py dump_file.mitm [output_dir]

Features:
- OpenAPI 3.0 specification generation
- Interactive timeline visualization
- Professional documentation output
"""

import sys
import argparse
from pathlib import Path

# Import our addons
from addons.api_extractor import APIExtractor
from addons.api_timeline import APITimeline
from parser import FlowParser


def generate_reports_from_file(dump_file: str, output_dir: str = "output"):
    """Generate enhanced reports from a captured dump file."""

    if not Path(dump_file).exists():
        print(f"❌ File not found: {dump_file}")
        return False

    print(f"📖 Processing capture file: {dump_file}")

    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

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
                    # Skip noise (OPTIONS, etc.)
                    if not api_extractor._is_filtered_noise(mock_flow):
                        if api_extractor._is_api_request(mock_flow):
                            api_extractor._extract_api_info(mock_flow)
                            api_count += 1
            except Exception as e:
                print(f"⚠️  API extraction error: {e}")

            # Process through timeline generator
            try:
                if not timeline_generator._is_blocked_traffic(mock_flow):
                    if timeline_generator._should_include_request(mock_flow):
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
            api_docs_dir = output_path / "api_docs"
            api_extractor.export_documentation(str(api_docs_dir))
            print(f"📚 API documentation generated: {api_docs_dir}/")
        else:
            print("⚠️  No API calls found for documentation")
    except Exception as e:
        print(f"❌ API documentation generation failed: {e}")
        success = False

    try:
        # Generate timeline
        if timeline_generator.api_calls:
            timeline_dir = output_path / "api_timeline"
            timeline_generator.generate_timeline_files(str(timeline_dir))
            print(f"🕒 Timeline generated: {timeline_dir}/timeline.html")
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
    """Main entry point for report generation."""
    if len(sys.argv) < 2:
        print("Usage: python generate_reports.py <dump_file.mitm> [output_dir]")
        print("       python generate_reports.py capture_20240101_120000.mitm")
        print("       python generate_reports.py capture_20240101_120000.mitm custom_output")
        sys.exit(1)

    dump_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"

    if not Path(dump_file).exists():
        print(f"❌ File not found: {dump_file}")
        sys.exit(1)

    print("🚀 Starting enhanced report generation...")
    print(f"📁 Input: {dump_file}")
    print(f"📁 Output: {output_dir}")
    print()

    try:
        success = generate_reports_from_file(dump_file, output_dir)

        if success:
            print()
            print("🎉 Report generation completed successfully!")
            print(f"📂 Open reports in: {output_dir}/")
            print(f"🚀 API Docs: {output_dir}/api_docs/viewer.html")
            print(f"🕒 Timeline: {output_dir}/api_timeline/timeline.html")
        else:
            print("❌ Some reports failed to generate")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n🛑 Report generation interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
