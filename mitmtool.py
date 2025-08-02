#!/usr/bin/env python3
"""
mitmtool.py - macOS Browser Proxy & Network Traffic Capture Tool (Refactored)

A Python-based system to programmatically control macOS proxy settings
and capture/analyze browser network traffic using mitmproxy.

This is the main entry point that coordinates all the different modules.
"""

import argparse
import sys
from pathlib import Path

# Import our modular components
from proxy_manager import ProxyManager
from traffic_manager import TrafficCapture
from traffic_viewer import TrafficViewer
from api_organizer import APIOrganizer


class MitmTool:
    """Main tool class that coordinates all functionality."""

    def __init__(self, proxy_host: str = "127.0.0.1", proxy_port: int = 8080):
        self.proxy_manager = ProxyManager(proxy_host, proxy_port)
        self.traffic_capture = TrafficCapture(proxy_host, proxy_port)
        self.traffic_viewer = TrafficViewer()
        self.api_organizer = APIOrganizer()
        self.default_dump_file = "capture.mitm"

    def enable_proxy(self) -> bool:
        """Enable proxy mode."""
        return self.proxy_manager.enable_proxy()

    def disable_proxy(self) -> bool:
        """Disable proxy mode."""
        return self.proxy_manager.disable_proxy()

    def check_proxy_status(self) -> None:
        """Check current proxy status."""
        self.proxy_manager.check_proxy_status()

    def start_capture(self, output_file: str = None) -> bool:
        """Start traffic capture."""
        return self.traffic_capture.start_capture(output_file)

    def view_capture(self, dump_file: str = None, filter_domain: str = None) -> None:
        """View captured traffic."""
        if dump_file is None:
            dump_file = self.default_dump_file
        self.traffic_viewer.view_capture(dump_file, filter_domain)

    def organize_apis(self, dump_file: str = None, output_dir: str = None) -> bool:
        """Organize API calls from dump file."""
        if dump_file is None:
            dump_file = self.default_dump_file
        if output_dir:
            self.api_organizer = APIOrganizer(output_dir)
        return self.api_organizer.organize_api_calls(dump_file)


def create_parser() -> argparse.ArgumentParser:
    """Create the command line argument parser."""
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
  python mitmtool.py organize                  # Organize APIs from capture.mitm
  python mitmtool.py organize --input api.mitm --output my_apis
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

    # Organize command
    organize_parser = subparsers.add_parser('organize', help='Organize API calls into directory structure')
    organize_parser.add_argument('--input', '-i', default=None,
                                help='Input dump file (default: capture.mitm)')
    organize_parser.add_argument('--output', '-o', default=None,
                                help='Output directory (default: api_calls)')

    return parser


def main():
    """Main function."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Default proxy settings
    tool = MitmTool()

    try:
        if args.command == 'enable':
            success = tool.enable_proxy()
            sys.exit(0 if success else 1)

        elif args.command == 'disable':
            success = tool.disable_proxy()
            sys.exit(0 if success else 1)

        elif args.command == 'status':
            tool.check_proxy_status()

        elif args.command == 'capture':
            success = tool.start_capture(args.output)
            sys.exit(0 if success else 1)

        elif args.command == 'view':
            tool.view_capture(args.input, args.domain)

        elif args.command == 'organize':
            success = tool.organize_apis(args.input, args.output)
            sys.exit(0 if success else 1)

        else:
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
