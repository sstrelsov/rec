#!/usr/bin/env python3
"""
serve_docs.py - Serve API Documentation with Local HTTP Server

This avoids CORS issues when viewing OpenAPI specs in the browser.
"""

import http.server
import socketserver
import webbrowser
import os
import sys
from pathlib import Path
from config import config

def serve_docs(docs_dir=None, port=None):
    """Start a local HTTP server in the api_docs directory."""

    # Use config defaults if not provided
    if docs_dir is None:
        docs_dir = f"{config.output_dir}/api_docs"
    if port is None:
        port = config.viewer_port

    docs_path = Path(docs_dir)

    # Check if api_docs exists
    if not docs_path.exists():
        print(f"❌ No api_docs directory found at: {docs_path.absolute()}")
        print("💡 Run 'make run' then 'make stop' to generate API documentation first.")
        return False

    # Get original directory to return to later
    original_dir = os.getcwd()

    # Change to api_docs directory
    os.chdir(docs_path)

    # Create server
    handler = http.server.SimpleHTTPRequestHandler

    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"🚀 Starting HTTP server on port {port}")
            print(f"📚 API Documentation: http://localhost:{port}/viewer.html")

            # Check if timeline exists
            timeline_path = docs_path.parent / "api_timeline" / "timeline.html"
            if timeline_path.exists():
                print(f"🕒 Timeline: http://localhost:{port}/../api_timeline/timeline.html")

            print()
            print("💡 Press Ctrl+C to stop the server")
            print(f"⚙️  Using config: {config.output_dir} (port {config.viewer_port})")

            # Open in browser
            webbrowser.open(f"http://localhost:{port}/viewer.html")

            # Start serving
            httpd.serve_forever()

    except KeyboardInterrupt:
        print("\n✅ Server stopped")
        return True
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {port} is already in use")
            print(f"💡 Try: python serve_docs.py --port {port + 1}")
            return False
        else:
            print(f"❌ Server error: {e}")
            return False
    finally:
        # Return to original directory
        os.chdir(original_dir)

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Serve API documentation with local HTTP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python serve_docs.py                         # Use config defaults ({config.output_dir}/api_docs, port {config.viewer_port})
  python serve_docs.py output/api_docs         # Specific directory
  python serve_docs.py -p 8080                 # Custom port
  python serve_docs.py --open-only             # Just open browser (if server running)

Configuration:
  Default settings loaded from .env file:
  - OUTPUT_DIR={config.output_dir}
  - VIEWER_PORT={config.viewer_port}

This solves CORS issues when viewing OpenAPI specs in browsers.
"""
    )

    parser.add_argument('docs_dir', nargs='?', default=None,
                       help=f'Path to api_docs directory (default: {config.output_dir}/api_docs)')
    parser.add_argument('-p', '--port', type=int, default=None,
                       help=f'Port to serve on (default: {config.viewer_port})')
    parser.add_argument('--open-only', action='store_true',
                       help='Just open browser without starting server')

    args = parser.parse_args()

    # Use command line args or fall back to config
    port = args.port if args.port is not None else config.viewer_port
    docs_dir = args.docs_dir if args.docs_dir is not None else f"{config.output_dir}/api_docs"

    if args.open_only:
        print(f"🌐 Opening browser to http://localhost:{port}/viewer.html")
        webbrowser.open(f"http://localhost:{port}/viewer.html")
        return

    print("🚀 Starting API Documentation Server...")
    print(f"📁 Serving: {docs_dir}")
    print(f"🔌 Port: {port}")
    success = serve_docs(docs_dir, port)

    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
