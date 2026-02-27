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
            print(f"error: getting network services: {e}")
            return []

    def enable_proxy(self) -> bool:
        """Enable HTTP/HTTPS proxy for all network services."""
        print(f"proxy: enabling {self.proxy_host}:{self.proxy_port}")

        services = self.get_network_services()
        if not services:
            print("error: no network services found")
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

                print(f"  + {service}")

            except subprocess.CalledProcessError as e:
                print(f"warning: failed to set proxy for {service}: {e}")
                success = False

        return success

    def disable_proxy(self) -> bool:
        """Disable HTTP/HTTPS proxy for all network services."""
        print("proxy: disabling")

        services = self.get_network_services()
        if not services:
            print("error: no network services found")
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

                print(f"  - {service}")

            except subprocess.CalledProcessError as e:
                print(f"warning: failed to disable proxy for {service}: {e}")
                success = False

        return success

    def check_proxy_status(self) -> List[Tuple[str, bool, str, str]]:
        """Check current proxy status for all network services.

        Returns:
            List of tuples: (service_name, is_enabled, server, port)
        """
        services = self.get_network_services()
        if not services:
            print("error: no network services found")
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
                    print(f"  on  {service} ({server}:{port})")
                else:
                    print(f"  off {service}")

            except subprocess.CalledProcessError as e:
                print(f"warning: error checking {service}: {e}")
                status_list.append((service, False, "", ""))

        return status_list
