#!/usr/bin/env python3
"""
mitmtool.py - macOS Browser Proxy & Network Traffic Capture Tool (Refactored)

A Python-based system to programmatically control macOS proxy settings
and capture/analyze browser network traffic using mitmproxy.

This is the main entry point that coordinates all the different modules.
"""

import argparse
import sys

# Import our modular components
from proxy_manager import ProxyManager
from capture import TrafficCapture


class MitmTool:
    """Main tool class that coordinates all functionality."""

    def __init__(self, proxy_host: str = "127.0.0.1", proxy_port: int = 8080, enhanced: bool = True):
        self.proxy_manager = ProxyManager(proxy_host, proxy_port)
        self.traffic_capture = TrafficCapture(proxy_host, proxy_port)
        self.traffic_capture.use_enhanced_addons = enhanced  # Control enhanced addons
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
        self.traffic_capture.view_capture(dump_file, filter_domain)

    def organize_apis(self, dump_file: str = None, output_dir: str = None) -> bool:
        """Organize API calls from dump file."""
        if dump_file is None:
            dump_file = self.default_dump_file
        return self.traffic_capture.organize_apis(dump_file, output_dir)

    def run_session(self, output_file: str = None) -> bool:
        """Start complete capture session (enable proxy + start capture)."""
        print("🚀 Starting unified capture session...")
        print("💡 This will enable proxy and start capturing automatically")

        # Enable proxy first
        if not self.enable_proxy():
            print("❌ Failed to enable proxy")
            return False

        print("✅ Proxy enabled successfully")

        # Start capture
        if not self.start_capture(output_file):
            print("❌ Failed to start capture, disabling proxy...")
            self.disable_proxy()
            return False

        return True

    def stop_session(self) -> bool:
        """Stop capture session and disable proxy."""
        print("🛑 Stopping session...")

        # Traffic capture handles stopping itself in the background
        # Just disable proxy here
        success = self.disable_proxy()

        if success:
            print("✅ Session stopped and proxy disabled")
        else:
            print("⚠️  Proxy disable failed - you may need to check manually")

        return success


def create_parser() -> argparse.ArgumentParser:
    """Create the command line argument parser."""
    parser = argparse.ArgumentParser(
        description="macOS Browser Proxy & Network Traffic Capture Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python mitmtool.py run                       # Start proxy & capture
  python mitmtool.py run --output api.mitm     # Start with custom filename
  python mitmtool.py stop                      # Stop capture & disable proxy
  python mitmtool.py status                    # Check current status
  python mitmtool.py view --input api.mitm     # View specific capture
  python mitmtool.py organize --input api.mitm # Organize specific capture

Recommended workflow:
  make run     # Even simpler - handles everything
  make stop    # Stop and organize automatically
  make view    # Browse organized results
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Main run command - replaces enable + capture
    run_parser = subparsers.add_parser('run', help='Start proxy and begin capturing (unified command)')
    run_parser.add_argument('--output', '-o', default=None,
                           help='Output dump file (default: capture_TIMESTAMP.mitm)')
    run_parser.add_argument('--enhanced', action='store_true', default=True,
                           help='Enable enhanced analysis (API docs, timeline, analytics blocking)')
    run_parser.add_argument('--basic', action='store_true', default=False,
                           help='Use basic capture only (disable enhanced features)')

    # Stop command - replaces disable (and optionally organizes)
    subparsers.add_parser('stop', help='Stop capture and disable proxy')

    # Status command
    subparsers.add_parser('status', help='Check current proxy and capture status')

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
        print("🕵️  mitmtool - Elegant Network Traffic Capture\n")
        print("💡 Quick start:")
        print("   python mitmtool.py run      # Start capturing")
        print("   python mitmtool.py stop     # Stop & organize")
        print("   python mitmtool.py view     # Browse results")
        print("\n📖 For full help:")
        print("   python mitmtool.py --help")
        print("\n🚀 Even simpler:")
        print("   make run     # Start everything")
        print("   make stop    # Stop & organize")
        print("   make view    # Browse results")
        return

    # Default proxy settings
    enhanced = not args.basic if hasattr(args, 'basic') else True
    tool = MitmTool(enhanced=enhanced)

    try:
        # New unified commands
        if args.command == 'run':
            if hasattr(args, 'basic') and args.basic:
                print("🔧 Running in basic mode (enhanced features disabled)")
            else:
                print("✨ Running with enhanced features (API docs, timeline, ad blocking)")
            success = tool.run_session(args.output)
            sys.exit(0 if success else 1)

        elif args.command == 'stop':
            success = tool.stop_session()
            sys.exit(0 if success else 1)

        elif args.command == 'status':
            tool.check_proxy_status()

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
