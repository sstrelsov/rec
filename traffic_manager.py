#!/usr/bin/env python3
"""
traffic_capture.py - Network Traffic Capture Management

Handles starting/stopping mitmproxy capture and managing capture processes.
"""

import subprocess
import signal
import sys
import time
import os
from pathlib import Path
from typing import Optional


class TrafficCapture:
    """Manages mitmproxy traffic capture sessions."""

    def __init__(self, proxy_host: str = "127.0.0.1", proxy_port: int = 8080):
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.mitmdump_process = None
        self.default_dump_file = "capture.mitm"

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

    def start_capture(self, output_file: Optional[str] = None) -> bool:
        """Start mitmdump to capture network traffic.

        Args:
            output_file: Path to save capture file. Uses default if None.

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
                self.stop_capture()
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

    def stop_capture(self) -> bool:
        """Stop the current capture session.

        Returns:
            True if capture was stopped successfully, False otherwise.
        """
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
            return True

        except Exception as e:
            print(f"❌ Error stopping capture: {e}")
            return False

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
