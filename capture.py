#!/usr/bin/env python3
"""
capture.py - Traffic Capture Management

Manages mitmdump subprocess for traffic capture with domain-scoped addons.
"""

import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Optional


# Resolve addon paths relative to this file's location
SCRIPT_DIR = Path(__file__).resolve().parent
ADDON_PATHS = [
    str(SCRIPT_DIR / "addons" / "traffic_analyzer.py"),
    str(SCRIPT_DIR / "addons" / "traffic_recorder.py"),
]


class TrafficCapture:
    """Manages mitmproxy traffic capture sessions."""

    def __init__(self, proxy_host: str = "127.0.0.1", proxy_port: int = 8080):
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.mitmdump_process = None

    def check_mitmproxy_available(self) -> bool:
        """Check if mitmdump is available on the system."""
        try:
            subprocess.run(["mitmdump", "--version"],
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("mitmdump not found. Install mitmproxy:")
            print("  brew install mitmproxy")
            return False

    def start_capture(self, output_dir: str) -> bool:
        """Start mitmdump to capture network traffic.

        Args:
            output_dir: Directory to save capture files into.

        Returns:
            True if capture started successfully, False otherwise.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        capture_file = str(output_path / f"capture_{timestamp}.mitm")

        print("recording")
        print(f"  output: {output_dir}")
        print(f"  proxy:  {self.proxy_host}:{self.proxy_port}")
        print("Press Ctrl+C to stop.")

        if not self.check_mitmproxy_available():
            return False

        try:
            # Kill any existing mitmdump processes
            try:
                subprocess.run(["pkill", "-f", "mitmdump"], capture_output=True)
                time.sleep(1)
            except Exception:
                pass

            cmd = [
                "mitmdump",
                "--listen-host", self.proxy_host,
                "--listen-port", str(self.proxy_port),
                "-w", capture_file,
            ]

            # Add addons
            for addon_path in ADDON_PATHS:
                if Path(addon_path).exists():
                    cmd.extend(["-s", addon_path])
                else:
                    print(f"Warning: addon not found: {addon_path}")

            self.mitmdump_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            time.sleep(2)

            if self.mitmdump_process.poll() is not None:
                stdout, _ = self.mitmdump_process.communicate()
                if stdout:
                    print(f"mitmdump failed to start:")
                    for line in stdout.strip().split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                        if 'address already in use' in line.lower():
                            print(f"  Port in use: {line}")
                        elif not line.startswith('['):
                            print(f"  {line}")
                else:
                    print("mitmdump failed to start (no error details)")
                return False

            for line in iter(self.mitmdump_process.stdout.readline, ''):
                if line:
                    print(line.strip())
            self.mitmdump_process.wait()

        except Exception as e:
            print(f"Error starting capture: {e}")
            return False

        return True

    def stop_capture(self) -> bool:
        """Stop the current capture session."""
        if self.mitmdump_process is None:
            return False

        try:
            self.mitmdump_process.terminate()
            try:
                self.mitmdump_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.mitmdump_process.kill()
                self.mitmdump_process.wait()

            self.mitmdump_process = None
            self._print_capture_summary()
            return True

        except Exception as e:
            print(f"Error stopping capture: {e}")
            return False

    def _print_capture_summary(self):
        """Print summary of recorded traffic after capture ends."""
        from config import config
        output_path = Path(config.output_dir)
        if not output_path.exists():
            return

        domain_dirs = [
            d for d in output_path.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        ]
        if domain_dirs:
            print("Recorded traffic:")
            for domain_dir in sorted(domain_dirs):
                call_dirs = [d for d in domain_dir.iterdir() if d.is_dir()]
                if call_dirs:
                    print(f"  {domain_dir.name}: {len(call_dirs)} calls")

    def is_capture_running(self) -> bool:
        """Check if a capture session is currently running."""
        return (self.mitmdump_process is not None and
                self.mitmdump_process.poll() is None)
