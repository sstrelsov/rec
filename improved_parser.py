#!/usr/bin/env python3
"""
Ultra-simple mitmproxy dump parser
Uses mitmdump's built-in formatting options
"""

import subprocess
import sys
import os

def simple_parse(dump_file: str, filter_domain: str = None):
    """Simple parser using mitmdump's built-in output formats"""

    if not os.path.exists(dump_file):
        print(f"❌ Dump file not found: {dump_file}")
        return

    print(f"🔄 Parsing {dump_file}...")

    try:
        # Method 1: Basic flow list
        print("\n" + "="*80)
        print("📋 BASIC FLOW LIST")
        print("="*80)

        cmd = ["mitmdump", "-r", dump_file, "-q"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            flow_count = 0

            for line in lines:
                if line.strip():
                    flow_count += 1
                    # Basic parsing of mitmdump output
                    if filter_domain and filter_domain.lower() not in line.lower():
                        continue

                    print(f"🔗 Flow #{flow_count}: {line}")

            print(f"\n📊 Total flows: {flow_count}")
            if filter_domain:
                print(f"🔍 Showing flows matching: {filter_domain}")

        else:
            print(f"❌ Error: {result.stderr}")

    except subprocess.TimeoutExpired:
        print("❌ Parsing timed out")
    except FileNotFoundError:
        print("❌ mitmdump not found. Install with: brew install mitmproxy")
    except Exception as e:
        print(f"❌ Error: {e}")

def detailed_parse(dump_file: str, max_flows: int = 10):
    """Get detailed info for first few flows"""

    print(f"\n" + "="*80)
    print("🔍 DETAILED FLOW ANALYSIS (First {max_flows} flows)")
    print("="*80)

    try:
        # Use mitmdump with verbose output for details
        cmd = ["mitmdump", "-r", dump_file, "-v"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            output_lines = result.stdout.split('\n')
            current_flow = 0

            for line in output_lines:
                if line.strip():
                    if any(method in line for method in ['GET ', 'POST ', 'PUT ', 'DELETE ']):
                        current_flow += 1
                        if current_flow <= max_flows:
                            print(f"\n🔗 Flow #{current_flow}:")
                            print(f"   {line}")
                    elif current_flow <= max_flows and line.startswith(' '):
                        print(f"   {line}")

                if current_flow > max_flows:
                    break

        else:
            print(f"❌ Error getting detailed info: {result.stderr}")

    except Exception as e:
        print(f"❌ Error in detailed analysis: {e}")

def export_to_text(dump_file: str, output_file: str = None):
    """Export flows to a readable text file"""

    if output_file is None:
        output_file = dump_file.replace('.mitm', '_readable.txt')

    print(f"\n💾 Exporting to {output_file}...")

    try:
        cmd = ["mitmdump", "-r", dump_file]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            with open(output_file, 'w') as f:
                f.write("MITMPROXY TRAFFIC CAPTURE\n")
                f.write("=" * 50 + "\n\n")
                f.write(result.stdout)

            print(f"✅ Exported to: {output_file}")
            print(f"📖 View with: cat {output_file}")

        else:
            print(f"❌ Export failed: {result.stderr}")

    except Exception as e:
        print(f"❌ Export error: {e}")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python simple_parser.py <dump_file> [domain_filter]")
        print("Example: python simple_parser.py capture.mitm")
        print("Example: python simple_parser.py capture.mitm nytimes.com")
        return

    dump_file = sys.argv[1]
    domain_filter = sys.argv[2] if len(sys.argv) > 2 else None

    # Basic parsing
    simple_parse(dump_file, domain_filter)

    # Detailed analysis
    detailed_parse(dump_file, max_flows=5)

    # Export option
    export_to_text(dump_file)

if __name__ == "__main__":
    main()
