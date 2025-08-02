#!/usr/bin/env python3
"""
capture.py - Unified Traffic Capture and Viewing

Consolidates traffic capture management and viewing capabilities.
"""

import subprocess
import signal
import sys
import time
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from parser import FlowParser
from config import config


class TrafficCapture:
    """Manages mitmproxy traffic capture sessions and viewing."""

    def __init__(self, proxy_host: str = "127.0.0.1", proxy_port: int = 8080):
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.mitmdump_process = None
        self.default_dump_file = "capture.mitm"
        self.parser = FlowParser()

        # Enhanced addons
        self.use_enhanced_addons = True  # Set to True to enable awesome features!
        self.addon_paths = [
            "addons/traffic_analyzer.py",
            "addons/api_extractor.py",
            "addons/api_timeline.py",
            "addons/traffic_recorder.py"
        ]

    def check_mitmproxy_available(self) -> bool:
        """Check if mitmdump is available on the system."""
        try:
            subprocess.run(["mitmdump", "--version"],
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ mitmdump not found. Please install mitmproxy:")
            print("   brew install mitmproxy")
            return False

    def start_capture(self, output_file: Optional[str] = None, try_alternative_ports: bool = True) -> bool:
        """Start mitmdump to capture network traffic.

        Args:
            output_file: Path to save capture file. Uses default if None.
            try_alternative_ports: Try alternative ports if default port is in use.

        Returns:
            True if capture started successfully, False otherwise.
        """
        if output_file is None:
            output_file = self.default_dump_file

        print(f"🎬 Starting traffic capture...")
        print(f"📁 Output file: {output_file}")
        print(f"🌐 Proxy listening on {self.proxy_host}:{self.proxy_port}")
        print("💡 Use your browser normally. Press Ctrl+C to stop capture.")

        if not self.check_mitmproxy_available():
            return False

        try:
            # Kill any existing mitmdump processes to free up the port
            try:
                subprocess.run(["pkill", "-f", "mitmdump"], capture_output=True)
                time.sleep(1)  # Give it a moment to clean up
            except:
                pass  # Ignore errors if no processes to kill

            cmd = [
                "mitmdump",
                "--listen-host", self.proxy_host,
                "--listen-port", str(self.proxy_port),
                "-w", output_file
            ]

            # Add enhanced addons if enabled
            if self.use_enhanced_addons:
                import os
                for addon_path in self.addon_paths:
                    if os.path.exists(addon_path):
                        cmd.extend(["-s", addon_path])
                        print(f"📊 Loaded addon: {addon_path}")
                    else:
                        print(f"⚠️  Addon not found: {addon_path}")

            print(f"🚀 Running: {' '.join(cmd)}")

            self.mitmdump_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            def signal_handler(signum, frame):
                print("\n🛑 Stopping capture...")
                self.stop_capture()
                print(f"💾 Traffic saved to: {output_file}")
                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)

            time.sleep(2)

            if self.mitmdump_process.poll() is not None:
                stdout, _ = self.mitmdump_process.communicate()
                if stdout:
                    print(f"❌ mitmdump failed to start:")
                    # Parse and display the most relevant error information
                    lines = stdout.strip().split('\n')
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        if 'error while attempting to bind' in line.lower() or 'address already in use' in line.lower():
                            print(f"💥 Port already in use: {line}")
                        elif 'try specifying a different port' in line.lower():
                            print(f"💡 Solution: {line}")
                            print(f"🔧 Quick fix: Try 'python mitmtool.py run' with a different port (mitmproxy will auto-select)")
                        elif not line.startswith('[') and 'error logged during startup' not in line.lower():
                            print(f"⚠️  {line}")
                else:
                    print("❌ mitmdump failed to start (no error details available)")
                return False

            print("✅ Capture started successfully!")
            print("🔗 Visit https://mitm.it to install the certificate if needed")

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

    def stop_capture(self) -> bool:
        """Stop the current capture session."""
        if self.mitmdump_process is None:
            print("⚠️  No capture process running")
            return False

        try:
            self.mitmdump_process.terminate()
            try:
                self.mitmdump_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("⚠️  Process didn't terminate gracefully, killing...")
                self.mitmdump_process.kill()
                self.mitmdump_process.wait()

            self.mitmdump_process = None
            print("✅ Capture stopped successfully")

            # Generate enhanced reports if addons were used
            if self.use_enhanced_addons:
                print("📊 Generating enhanced reports...")
                self._generate_enhanced_reports()

            return True

        except Exception as e:
            print(f"❌ Error stopping capture: {e}")
            return False

    def _generate_enhanced_reports(self):
        """Generate reports from enhanced addons."""
        try:
            # The addons generate their own files, just notify the user
            import os

            reports_found = []

            # Check for API documentation
            api_docs_path = f"{config.output_dir}/api_docs"
            if os.path.exists(api_docs_path):
                reports_found.append(f"📚 API Documentation: {api_docs_path}/")

            # Check for timeline
            timeline_path = f"{config.output_dir}/api_timeline"
            if os.path.exists(timeline_path):
                reports_found.append(f"🕒 API Timeline: {timeline_path}/timeline.html")
            
            # Check for traffic recordings
            output_path = Path(config.output_dir)
            if output_path.exists():
                domain_dirs = [d for d in output_path.iterdir() if d.is_dir() and d.name not in ['api_docs', 'api_timeline']]
                if domain_dirs:
                    reports_found.append(f"📡 Network Traffic Recordings: {config.output_dir}/")
                    for domain_dir in domain_dirs[:3]:  # Show first 3 domains
                        call_dirs = [d for d in domain_dir.iterdir() if d.is_dir()]
                        reports_found.append(f"   • {domain_dir.name}: {len(call_dirs)} calls")
                    if len(domain_dirs) > 3:
                        reports_found.append(f"   ... and {len(domain_dirs) - 3} more domains")

            if reports_found:
                print("✨ Enhanced reports generated:")
                for report in reports_found:
                    print(f"  {report}")
                print("💡 Usage:")
                print(f"  📚 View API docs: python serve_docs.py")
                print(f"  🕒 Open timeline in browser")  
                print(f"  📡 Test calls: cd {config.output_dir}/<domain>/<call_dir> && ./request.sh")
            else:
                print("📊 Enhanced analysis completed (check console output)")

        except Exception as e:
            print(f"⚠️  Could not check for enhanced reports: {e}")

    def is_capture_running(self) -> bool:
        """Check if a capture session is currently running."""
        return (self.mitmdump_process is not None and
                self.mitmdump_process.poll() is None)

    def get_capture_status(self) -> dict:
        """Get status information about the current capture session."""
        return {
            "running": self.is_capture_running(),
            "process_id": self.mitmdump_process.pid if self.is_capture_running() else None,
            "proxy_host": self.proxy_host,
            "proxy_port": self.proxy_port
        }

    def view_capture(self, dump_file: str,
                    filter_domain: Optional[str] = None,
                    max_flows: int = 20) -> None:
        """View and analyze captured traffic."""
        # Use simple view for quick overview
        if filter_domain or max_flows <= 5:
            self.parser.simple_view(dump_file, filter_domain)
            return

        # Use detailed view for comprehensive analysis
        print(f"📖 Reading traffic dump: {dump_file}")
        flows = self.parser.parse_flows(dump_file)

        if not flows:
            print("❌ No flows found or error parsing dump file")
            return

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
        summary = self.parser.get_summary(flows)

        print("🌐 Domains captured:")
        for domain, count in sorted(summary["domains"].items(),
                                   key=lambda x: x[1], reverse=True):
            print(f"  • {domain}: {count} requests")
        print()

        if summary["methods"]:
            print("📋 HTTP Methods:")
            for method, count in sorted(summary["methods"].items()):
                print(f"  • {method}: {count} requests")
            print()

        if summary["status_codes"]:
            print("📊 Status Codes:")
            for status, count in sorted(summary["status_codes"].items()):
                status_emoji = self._get_status_emoji(status)
                print(f"  • {status} {status_emoji}: {count} responses")
            print()

        total_size_mb = summary["total_size"] / (1024 * 1024)
        print(f"📈 Total Response Size: {total_size_mb:.2f} MB")

        if summary["time_range"]["start"] and summary["time_range"]["end"]:
            import time as time_module
            start_time = time_module.strftime('%H:%M:%S', time_module.localtime(summary["time_range"]["start"]))
            end_time = time_module.strftime('%H:%M:%S', time_module.localtime(summary["time_range"]["end"]))
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

            headers = flow.get('response_headers', {})
            content_type = headers.get('content-type', headers.get('Content-Type', 'N/A'))
            print(f"   Content-Type: {content_type}")

            if 'json' in content_type.lower():
                self._display_json_preview(flow)

            timestamp = flow.get('timestamp', 0)
            if timestamp:
                import time as time_module
                time_str = time_module.strftime('%Y-%m-%d %H:%M:%S', time_module.localtime(timestamp))
                print(f"   Timestamp: {time_str}")

            print()

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

