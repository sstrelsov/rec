#!/usr/bin/env python3
"""
proxy_manager.py - macOS Network Proxy Management

Handles enabling/disabling HTTP/HTTPS proxy settings for all network services.
"""

import subprocess
from typing import List, Tuple


class ProxyManager:
    """Manages macOS network proxy settings."""

    def __init__(self, proxy_host: str = "127.0.0.1", proxy_port: int = 8080):
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port

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

    def check_proxy_status(self) -> List[Tuple[str, bool, str, str]]:
        """Check current proxy status for all network services.

        Returns:
            List of tuples: (service_name, is_enabled, server, port)
        """
        print("🔍 Checking proxy status...")

        services = self.get_network_services()
        if not services:
            print("❌ No network services found")
            return []

        status_list = []
        for service in services:
            try:
                # Check HTTP proxy
                result = subprocess.run([
                    "networksetup", "-getwebproxy", service
                ], capture_output=True, text=True, check=True)

                lines = result.stdout.strip().split('\n')
                enabled = any("Yes" in line for line in lines if "Enabled" in line)

                server = ""
                port = ""
                if enabled:
                    server_line = next((line for line in lines if "Server" in line), "")
                    port_line = next((line for line in lines if "Port" in line), "")
                    server = server_line.split()[-1] if server_line else "unknown"
                    port = port_line.split()[-1] if port_line else "unknown"

                status_list.append((service, enabled, server, port))

                if enabled:
                    print(f"🟢 {service}: ENABLED ({server}:{port})")
                else:
                    print(f"🔴 {service}: DISABLED")

            except subprocess.CalledProcessError as e:
                print(f"⚠️  Error checking {service}: {e}")
                status_list.append((service, False, "", ""))

        return status_list
