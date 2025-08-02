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
            "addons/api_timeline.py"
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
            if os.path.exists("api_docs"):
                reports_found.append("📚 API Documentation: api_docs/")

            # Check for timeline
            if os.path.exists("api_timeline"):
                reports_found.append("🕒 API Timeline: api_timeline/timeline.html")

            if reports_found:
                print("✨ Enhanced reports generated:")
                for report in reports_found:
                    print(f"  {report}")
                print("💡 Open timeline.html in your browser for the chronological view!")
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

    def organize_apis(self, dump_file: str, output_dir: str = None) -> bool:
        """Organize API calls from dump file into directory structure."""
        if not dump_file or not Path(dump_file).exists():
            print(f"❌ File not found: {dump_file}")
            return False

        if output_dir is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = f"api_calls_{timestamp}"

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        print(f"🗂️  Organizing API calls from {dump_file}")
        print(f"📁 Output directory: {output_path.absolute()}")

        try:
            flows = self.parser.parse_flows(dump_file)
            if not flows:
                print("❌ No flows found")
                return False

            domain_counters = {}

            for flow in flows:
                if flow.get('error'):
                    continue  # Skip error flows

                self._organize_single_flow(flow, output_path, domain_counters)

            print(f"\n✅ API calls organized in: {output_path.absolute()}")
            self._show_organization_summary(output_path)
            return True

        except Exception as e:
            print(f"❌ Error organizing APIs: {e}")
            return False

    def _organize_single_flow(self, flow: Dict[str, Any], output_path: Path, domain_counters: Dict) -> None:
        """Organize a single flow into the directory structure."""
        domain = self._sanitize_name(flow.get('host', 'unknown'))
        domain_dir = output_path / domain
        domain_dir.mkdir(exist_ok=True)

        method = flow.get('method', 'GET').lower()
        path = self._sanitize_name(flow.get('path', '/'))

        # Include context in the directory name for better organization
        context = flow.get('context', 'unknown')
        context_prefix = "api" if context == "api" else "browser" if context == "browser" else "unknown"
        base_name = f"{context_prefix}_{method}_{path}"

        # Handle duplicate names
        if domain not in domain_counters:
            domain_counters[domain] = {}
        counter = domain_counters[domain].get(base_name, 0)
        domain_counters[domain][base_name] = counter + 1

        call_name = base_name if counter == 0 else f"{base_name}_{counter + 1}"
        call_dir = domain_dir / call_name
        call_dir.mkdir(exist_ok=True)

        # Write context metadata
        self._write_context_metadata(flow, call_dir)

        # Write HTTPie command
        self._write_httpie_command(flow, call_dir)

        # Write response
        self._write_response_file(flow, call_dir)

        # Enhanced status display with context
        context_icon = "⚡" if context == "api" else "🌐" if context == "browser" else "❓"
        print(f"📁 {domain}/{call_name} - {context_icon} {method.upper()} {flow.get('path', '/')} -> {flow.get('status_code', '?')}")

    def _sanitize_name(self, name: str) -> str:
        """Convert name to safe directory/file name."""
        import re
        name = re.sub(r'[^\w\-_.]', '_', name.split('?')[0][:100]).strip('_')
        return name or "root"

    def _write_httpie_command(self, flow: Dict[str, Any], call_dir: Path) -> None:
        """Write HTTPie command to request file."""
        method = flow.get('method', 'GET')
        url = flow.get('url', '')

        parts = ["http"] if method == "GET" else ["http", method]
        parts.append(url)

        # Add headers (skip common ones)
        skip_headers = {'host', 'content-length', 'connection', 'accept-encoding'}
        headers = flow.get('request_headers', {})
        for name, value in headers.items():
            if name.lower() not in skip_headers:
                escaped_value = value.replace('"', '\\"')
                parts.append(f'{name}:"{escaped_value}"')

        # Add body for POST/PUT/PATCH
        if method in ["POST", "PUT", "PATCH"] and flow.get('request_content'):
            content = flow['request_content']
            if not content.startswith('<binary'):
                try:
                    # Try to format as JSON
                    import json
                    json_body = json.dumps(json.loads(content), separators=(',', ':'))
                    parts.append(f'"{json_body}"')
                except:
                    parts.append(f'"{content.replace('"', '\\"')}"')

        request_file = call_dir / "request"
        with open(request_file, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write(f"# {method} {url}\n")
            f.write(f"# Status: {flow.get('status_code', '?')}\n\n")
            f.write(" \\\n  ".join(parts))
            f.write("\n")

        # Make executable
        import stat
        request_file.chmod(request_file.stat().st_mode | stat.S_IEXEC)

    def _write_response_file(self, flow: Dict[str, Any], call_dir: Path) -> None:
        """Write response content to file."""
        content_type = flow.get('response_headers', {}).get('content-type', '')
        ext = self._get_file_extension(content_type)
        response_file = call_dir / f"response{ext}"

        response_content = flow.get('response_content')

        # Check if we have actual content (not just None)
        if response_content is not None and response_content != "":
            if response_content.startswith('<binary'):
                # Binary content - write info message
                with open(response_file, 'w') as f:
                    f.write(f"# Binary response ({flow.get('status_code', '?')})\n")
                    f.write(f"# Content-Type: {content_type}\n")
                    f.write(f"# {response_content}\n")
            elif 'json' in content_type.lower():
                # JSON content - try to format
                try:
                    import json
                    with open(response_file, 'w') as f:
                        json.dump(json.loads(response_content), f, indent=2)
                except:
                    with open(response_file, 'w') as f:
                        f.write(response_content)
            else:
                # Regular text content
                with open(response_file, 'w') as f:
                    f.write(response_content)
        else:
            # Empty response or None
            with open(response_file, 'w') as f:
                f.write(f"# Empty response ({flow.get('status_code', '?')})\n")
                f.write(f"# Content-Type: {content_type}\n")

    def _get_file_extension(self, content_type: str) -> str:
        """Get appropriate file extension based on content type."""
        if not content_type:
            return ".txt"
        ct = content_type.lower().split(';')[0]
        extensions = {
            'application/json': '.json',
            'text/html': '.html',
            'text/javascript': '.js',
            'application/javascript': '.js',
            'application/xml': '.xml',
            'text/xml': '.xml'
        }
        return extensions.get(ct, '.txt')

    def _write_context_metadata(self, flow: Dict[str, Any], call_dir: Path) -> None:
        """Write context metadata file with information about the request type."""
        context = flow.get('context', 'unknown')
        context_info = {
            'browser': {'name': 'Browser', 'icon': '🌐', 'description': 'User browsing web pages, loading static assets'},
            'api': {'name': 'API', 'icon': '⚡', 'description': 'Frontend-backend or app-to-app communication'},
            'unknown': {'name': 'Unknown', 'icon': '❓', 'description': 'Could not determine request context'}
        }.get(context, {'name': 'Unknown', 'icon': '❓', 'description': 'Could not determine request context'})

        metadata = {
            'context': context,
            'context_name': context_info['name'],
            'context_icon': context_info['icon'],
            'context_description': context_info['description'],
            'timestamp': flow.get('timestamp', ''),
            'method': flow.get('method', ''),
            'url': flow.get('url', ''),
            'status_code': flow.get('status_code', ''),
            'response_size': flow.get('response_size', 0)
        }

        metadata_file = call_dir / 'metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

    def _show_organization_summary(self, output_path: Path) -> None:
        """Show summary of organized API calls."""
        try:
            dirs = [d for d in output_path.iterdir() if d.is_dir()]
            total_calls = sum(len([f for f in d.iterdir() if f.is_dir()]) for d in dirs)

            print(f"\n📊 Summary:")
            print(f"  • {len(dirs)} domains")
            print(f"  • {total_calls} API calls")
            print(f"\n💡 Usage:")
            print(f"  cd {output_path}")
            print(f"  ./*/request        # Run HTTPie commands")
            print(f"  cat */response.*   # View responses")

        except Exception:
            pass
