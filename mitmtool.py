#!/usr/bin/env python3
"""
mitmtool.py - macOS Browser Proxy & Network Traffic Capture Tool

A Python-based system to programmatically control macOS proxy settings
and capture/analyze browser network traffic using mitmproxy.

Usage:
    python mitmtool.py enable              # Enable proxy mode
    python mitmtool.py capture [--output file.mitm]  # Start capturing traffic
    python mitmtool.py disable             # Disable proxy mode
    python mitmtool.py view [--input file.mitm]      # View captured traffic
    python mitmtool.py status              # Check current proxy status
"""

import argparse
import subprocess
import sys
import os
import json
import signal
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import tempfile


class MitmTool:
    def __init__(self):
        self.proxy_host = "127.0.0.1"
        self.proxy_port = 8080
        self.default_dump_file = "capture.mitm"
        self.mitmdump_process = None

    def get_network_services(self) -> List[str]:
        """Get list of network services that can have proxy settings."""
        try:
            result = subprocess.run(
                ["networksetup", "-listallnetworkservices"],
                capture_output=True,
                text=True,
                check=True
            )
            services = []
            for line in result.stdout.strip().split('\n')[1:]:  # Skip header
                if line and not line.startswith('*'):
                    services.append(line.strip())
            return services
        except subprocess.CalledProcessError as e:
            print(f"❌ Error getting network services: {e}")
            return []

    def enable_proxy(self) -> bool:
        """Enable HTTP/HTTPS proxy for all network services."""
        print(f"🔧 Enabling proxy {self.proxy_host}:{self.proxy_port}...")

        services = self.get_network_services()
        if not services:
            print("❌ No network services found")
            return False

        success = True
        for service in services:
            try:
                # Enable HTTP proxy
                subprocess.run([
                    "networksetup", "-setwebproxy", service,
                    self.proxy_host, str(self.proxy_port)
                ], check=True, capture_output=True)

                # Enable HTTPS proxy
                subprocess.run([
                    "networksetup", "-setsecurewebproxy", service,
                    self.proxy_host, str(self.proxy_port)
                ], check=True, capture_output=True)

                print(f"✅ Enabled proxy for: {service}")

            except subprocess.CalledProcessError as e:
                print(f"⚠️  Failed to set proxy for {service}: {e}")
                success = False

        if success:
            print(f"🎉 Proxy enabled! Browser traffic will route through {self.proxy_host}:{self.proxy_port}")
            print("💡 Make sure mitmproxy certificate is installed in your browser")

        return success

    def disable_proxy(self) -> bool:
        """Disable HTTP/HTTPS proxy for all network services."""
        print("🔧 Disabling proxy...")

        services = self.get_network_services()
        if not services:
            print("❌ No network services found")
            return False

        success = True
        for service in services:
            try:
                # Disable HTTP proxy
                subprocess.run([
                    "networksetup", "-setwebproxystate", service, "off"
                ], check=True, capture_output=True)

                # Disable HTTPS proxy
                subprocess.run([
                    "networksetup", "-setsecurewebproxystate", service, "off"
                ], check=True, capture_output=True)

                print(f"✅ Disabled proxy for: {service}")

            except subprocess.CalledProcessError as e:
                print(f"⚠️  Failed to disable proxy for {service}: {e}")
                success = False

        if success:
            print("🎉 Proxy disabled! Browser traffic restored to normal")

        return success

    def check_proxy_status(self) -> None:
        """Check current proxy status for all network services."""
        print("🔍 Checking proxy status...")

        services = self.get_network_services()
        if not services:
            print("❌ No network services found")
            return

        for service in services:
            try:
                # Check HTTP proxy
                result = subprocess.run([
                    "networksetup", "-getwebproxy", service
                ], capture_output=True, text=True, check=True)

                lines = result.stdout.strip().split('\n')
                enabled = any("Yes" in line for line in lines if "Enabled" in line)

                if enabled:
                    server_line = next((line for line in lines if "Server" in line), "")
                    port_line = next((line for line in lines if "Port" in line), "")
                    print(f"🟢 {service}: ENABLED ({server_line.split()[-1] if server_line else 'unknown'}:{port_line.split()[-1] if port_line else 'unknown'})")
                else:
                    print(f"🔴 {service}: DISABLED")

            except subprocess.CalledProcessError as e:
                print(f"⚠️  Error checking {service}: {e}")

    def start_capture(self, output_file: str = None) -> bool:
        """Start mitmdump to capture network traffic."""
        if output_file is None:
            output_file = self.default_dump_file

        print(f"🎬 Starting traffic capture...")
        print(f"📁 Output file: {output_file}")
        print(f"🌐 Proxy listening on {self.proxy_host}:{self.proxy_port}")
        print("💡 Use your browser normally. Press Ctrl+C to stop capture.")

        try:
            # Check if mitmdump is available
            subprocess.run(["mitmdump", "--version"],
                         capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ mitmdump not found. Please install mitmproxy:")
            print("   brew install mitmproxy")
            return False

        try:
            # Start mitmdump with options
            cmd = [
                "mitmdump",
                "--listen-host", self.proxy_host,
                "--listen-port", str(self.proxy_port),
                "--set", f"confdir={Path.home()}/.mitmproxy",
                "-w", output_file,
                "--set", "stream_large_bodies=1",  # Stream large responses
                "--set", "flow_detail=3"  # Capture full details
            ]

            print(f"🚀 Running: {' '.join(cmd)}")

            # Start the process
            self.mitmdump_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Set up signal handler for graceful shutdown
            def signal_handler(signum, frame):
                print("\n🛑 Stopping capture...")
                if self.mitmdump_process:
                    self.mitmdump_process.terminate()
                    try:
                        self.mitmdump_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.mitmdump_process.kill()
                print(f"💾 Traffic saved to: {output_file}")
                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)

            # Wait a moment for startup
            time.sleep(2)

            if self.mitmdump_process.poll() is not None:
                output, _ = self.mitmdump_process.communicate()
                print(f"❌ mitmdump failed to start:\n{output}")
                return False

            print("✅ Capture started successfully!")
            print("🔗 Visit https://mitm.it to install the certificate if needed")

            # Keep the script running and show live output
            try:
                for line in iter(self.mitmdump_process.stdout.readline, ''):
                    if line:
                        print(f"📡 {line.strip()}")

                self.mitmdump_process.wait()

            except KeyboardInterrupt:
                signal_handler(signal.SIGINT, None)

        except Exception as e:
            print(f"❌ Error starting capture: {e}")
            return False

        return True

    def parse_mitm_dump(self, dump_file: str) -> List[Dict[str, Any]]:
        """Parse mitmproxy dump file and extract flow data."""
        if not os.path.exists(dump_file):
            print(f"❌ Dump file not found: {dump_file}")
            return []

        try:
            # Use mitmproxy's mitmdump to convert binary dump to readable format
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as tmp_file:
                cmd = [
                    "mitmdump",
                    "-r", dump_file,
                    "-s", "-",  # Read from stdin
                    "--set", "flow_detail=3"
                ]

                # Create a simple script to output JSON
                script = '''
import json
from mitmproxy import http

def response(flow: http.HTTPFlow) -> None:
    flow_data = {
        "timestamp": flow.request.timestamp_start,
        "method": flow.request.method,
        "url": flow.request.pretty_url,
        "host": flow.request.pretty_host,
        "path": flow.request.path,
        "request_headers": dict(flow.request.headers),
        "request_content": flow.request.get_text() if flow.request.content else None,
        "status_code": flow.response.status_code if flow.response else None,
        "response_headers": dict(flow.response.headers) if flow.response else None,
        "response_content": flow.response.get_text() if flow.response and flow.response.content else None,
        "response_size": len(flow.response.content) if flow.response and flow.response.content else 0
    }
    print(json.dumps(flow_data))
'''

                # Run mitmdump with the script
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=tmp_file,
                    stderr=subprocess.PIPE,
                    text=True
                )

                stdout, stderr = process.communicate(input=script)

                if process.returncode != 0:
                    print(f"❌ Error parsing dump: {stderr}")
                    return []

            # Read the JSON output
            flows = []
            try:
                with open(tmp_file.name, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                flows.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
            finally:
                os.unlink(tmp_file.name)

            return flows

        except Exception as e:
            print(f"❌ Error parsing dump file: {e}")
            return []

    def view_capture(self, dump_file: str = None, filter_domain: str = None) -> None:
        """View and analyze captured traffic."""
        if dump_file is None:
            dump_file = self.default_dump_file

        print(f"📖 Reading traffic dump: {dump_file}")

        flows = self.parse_mitm_dump(dump_file)

        if not flows:
            print("❌ No flows found or error parsing dump file")
            return

        # Filter by domain if specified
        if filter_domain:
            flows = [f for f in flows if filter_domain.lower() in f.get('host', '').lower()]
            print(f"🔍 Filtered to {len(flows)} flows matching '{filter_domain}'")

        print(f"\n📊 Found {len(flows)} HTTP flows\n")

        # Group by domain
        domains = {}
        for flow in flows:
            domain = flow.get('host', 'unknown')
            if domain not in domains:
                domains[domain] = []
            domains[domain].append(flow)

        # Display summary
        print("🌐 Domains captured:")
        for domain, domain_flows in domains.items():
            print(f"  • {domain}: {len(domain_flows)} requests")
        print()

        # Display detailed flows
        for i, flow in enumerate(flows, 1):
            print(f"🔗 Flow #{i}")
            print(f"   Method: {flow.get('method', 'N/A')}")
            print(f"   URL: {flow.get('url', 'N/A')}")
            print(f"   Status: {flow.get('status_code', 'N/A')}")
            print(f"   Size: {flow.get('response_size', 0)} bytes")

            # Show interesting headers
            headers = flow.get('response_headers', {})
            content_type = headers.get('content-type', headers.get('Content-Type', 'N/A'))
            print(f"   Content-Type: {content_type}")

            # Show request/response content preview for JSON APIs
            if 'json' in content_type.lower():
                response_content = flow.get('response_content')
                if response_content:
                    try:
                        json_data = json.loads(response_content)
                        preview = json.dumps(json_data, indent=2)[:200]
                        if len(preview) == 200:
                            preview += "..."
                        print(f"   JSON Preview:\n{preview}")
                    except:
                        pass

            print(f"   Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(flow.get('timestamp', 0)))}")
            print()

            # Stop after 20 flows to avoid overwhelming output
            if i >= 20:
                remaining = len(flows) - i
                if remaining > 0:
                    print(f"... and {remaining} more flows")
                break


def main():
    parser = argparse.ArgumentParser(
        description="macOS Browser Proxy & Network Traffic Capture Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python mitmtool.py enable                    # Enable proxy mode
  python mitmtool.py capture                   # Start capturing to capture.mitm
  python mitmtool.py capture --output api.mitm # Start capturing to api.mitm
  python mitmtool.py disable                   # Disable proxy mode
  python mitmtool.py view                      # View capture.mitm
  python mitmtool.py view --input api.mitm     # View api.mitm
  python mitmtool.py view --domain airdna.co   # Filter by domain
  python mitmtool.py status                    # Check proxy status
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Enable command
    subparsers.add_parser('enable', help='Enable browser proxy mode')

    # Disable command
    subparsers.add_parser('disable', help='Disable browser proxy mode')

    # Status command
    subparsers.add_parser('status', help='Check current proxy status')

    # Capture command
    capture_parser = subparsers.add_parser('capture', help='Start capturing network traffic')
    capture_parser.add_argument('--output', '-o', default=None,
                               help='Output dump file (default: capture.mitm)')

    # View command
    view_parser = subparsers.add_parser('view', help='View captured traffic')
    view_parser.add_argument('--input', '-i', default=None,
                            help='Input dump file (default: capture.mitm)')
    view_parser.add_argument('--domain', '-d', default=None,
                            help='Filter by domain name')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    tool = MitmTool()

    try:
        if args.command == 'enable':
            tool.enable_proxy()
        elif args.command == 'disable':
            tool.disable_proxy()
        elif args.command == 'status':
            tool.check_proxy_status()
        elif args.command == 'capture':
            tool.start_capture(args.output)
        elif args.command == 'view':
            tool.view_capture(args.input, args.domain)
        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
