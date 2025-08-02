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

def serve_docs(port=8000):
    """Start a local HTTP server in the api_docs directory."""

    # Check if api_docs exists
    if not Path("api_docs").exists():
        print("❌ No api_docs directory found!")
        print("💡 Run 'make run' then 'make stop' to generate API documentation first.")
        return False

    # Change to api_docs directory
    os.chdir("api_docs")

    # Create server
    handler = http.server.SimpleHTTPRequestHandler

    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"🚀 Starting HTTP server on port {port}")
            print(f"📚 API Documentation: http://localhost:{port}/viewer.html")
            print(f"🕒 Timeline: http://localhost:{port}/../api_timeline/timeline.html")
            print()
            print("💡 Press Ctrl+C to stop the server")

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

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Serve API documentation with local HTTP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python serve_docs.py              # Default port 8000
  python serve_docs.py -p 8080      # Custom port
  python serve_docs.py --open-only  # Just open browser (if server running)

This solves CORS issues when viewing OpenAPI specs in browsers.
"""
    )

    parser.add_argument('-p', '--port', type=int, default=8000,
                       help='Port to serve on (default: 8000)')
    parser.add_argument('--open-only', action='store_true',
                       help='Just open browser without starting server')

    args = parser.parse_args()

    if args.open_only:
        print(f"🌐 Opening browser to http://localhost:{args.port}/viewer.html")
        webbrowser.open(f"http://localhost:{args.port}/viewer.html")
        return

    print("🚀 Starting API Documentation Server...")
    success = serve_docs(args.port)

    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
