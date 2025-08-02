#!/usr/bin/env python3
"""
api_organizer.py - API Call Organization

Organizes mitmproxy captures into directory structure with HTTPie commands.
"""

import subprocess
import os
import json
import re
import stat
import tempfile
from pathlib import Path
from typing import Dict, Any
from urllib.parse import urlparse


class APIOrganizer:
    """Organizes API calls into directory structure."""

    def __init__(self, output_dir: str = "api_calls"):
        self.output_dir = Path(output_dir)

    def sanitize_path_name(self, name: str) -> str:
        """Convert URL path to safe directory name."""
        # Remove query parameters and fragments
        name = name.split('?')[0].split('#')[0]
        # Replace slashes and special chars with underscores
        name = re.sub(r'[^\w\-_.]', '_', name)
        # Remove leading/trailing underscores
        name = name.strip('_')
        # Limit length
        if len(name) > 100:
            name = name[:100]
        # Ensure it's not empty
        if not name:
            name = "root"
        return name

    def get_response_extension(self, content_type: str) -> str:
        """Get appropriate file extension based on content type."""
        if not content_type:
            return ".txt"

        content_type = content_type.lower().split(';')[0].strip()

        extension_map = {
            'application/json': '.json',
            'application/ld+json': '.json',
            'text/json': '.json',
            'text/html': '.html',
            'application/xhtml+xml': '.html',
            'application/xml': '.xml',
            'text/xml': '.xml',
            'text/plain': '.txt',
            'text/csv': '.csv',
            'text/css': '.css',
            'text/javascript': '.js',
            'application/javascript': '.js',
            'application/x-javascript': '.js',
            'image/png': '.png',
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/gif': '.gif',
            'image/svg+xml': '.svg',
            'image/webp': '.webp',
            'application/pdf': '.pdf',
            'application/zip': '.zip',
            'font/woff': '.woff',
            'font/woff2': '.woff2',
            'application/octet-stream': '.bin',
        }

        return extension_map.get(content_type, '.txt')

    def generate_httpie_command(self, flow: Dict[str, Any]) -> str:
        """Generate HTTPie command string from flow data."""
        method = flow.get('method', 'GET').upper()
        url = flow.get('url', '')

        if method == "GET":
            cmd_parts = ["http"]
        else:
            cmd_parts = ["http", method]

        cmd_parts.append(url)

        # Skip common headers that HTTPie adds automatically
        skip_headers = {
            'host', 'content-length', 'connection', 'accept-encoding',
            'cache-control', 'pragma', 'upgrade-insecure-requests'
        }

        # Add headers
        headers = flow.get('request_headers', {})
        for name, value in headers.items():
            if name.lower() not in skip_headers:
                # Escape quotes in header values
                escaped_value = value.replace('"', '\\"')
                cmd_parts.append(f'{name}:"{escaped_value}"')

        # Add request body for POST/PUT/PATCH
        if method in ["POST", "PUT", "PATCH"]:
            request_content = flow.get('request_content')
            if request_content:
                try:
                    # Try to parse as JSON for pretty formatting
                    json_data = json.loads(request_content)
                    json_str = json.dumps(json_data, separators=(',', ':'))
                    cmd_parts.append(f"'{json_str}'")
                except (json.JSONDecodeError, TypeError):
                    # Not JSON, escape as string
                    escaped_body = request_content.replace("'", "'\"'\"'")
                    cmd_parts.append(f"'{escaped_body}'")

        return " \\\n  ".join(cmd_parts)

    def organize_api_calls(self, dump_file: str) -> bool:
        """Organize mitmproxy dump into directory structure.

        Args:
            dump_file: Path to mitmproxy dump file.

        Returns:
            True if organization was successful, False otherwise.
        """
        if not os.path.exists(dump_file):
            print(f"❌ File not found: {dump_file}")
            return False

        # Create base output directory
        self.output_dir.mkdir(exist_ok=True)

        print(f"🔄 Organizing API calls from {dump_file}")
        print(f"📁 Output directory: {self.output_dir.absolute()}")

        # Create the mitmdump organization script
        script_content = self._create_organization_script()

        # Write script to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            script_path = f.name

        try:
            # Run mitmdump with the organization script
            cmd = ["mitmdump", "-s", script_path, "-r", dump_file]

            print(f"🚀 Processing flows...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode == 0:
                print(result.stdout)
                print(f"\n✅ API calls organized in: {self.output_dir.absolute()}")

                # Show directory structure
                print(f"\n📂 Directory structure:")
                self.show_tree_structure(self.output_dir)

                print(f"\n💡 Usage:")
                print(f"  cd {self.output_dir}")
                print(f"  ./api.example.com/get_users/request      # Run HTTPie command")
                print(f"  cat api.example.com/get_users/response.json  # View response")

                return True
            else:
                print(f"❌ Error: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("❌ Processing timed out")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        finally:
            # Clean up temp file
            try:
                os.unlink(script_path)
            except:
                pass

    def _create_organization_script(self) -> str:
        """Create the mitmproxy script for organizing API calls."""
        return f'''
import json
import re
import stat
from pathlib import Path
from urllib.parse import urlparse

output_dir = Path('{self.output_dir}')
flow_count = 0
domain_counters = {{}}

def sanitize_path_name(name):
    """Convert URL path to safe directory name"""
    name = name.split('?')[0].split('#')[0]
    name = re.sub(r'[^\\w\\-_.]', '_', name)
    name = name.strip('_')
    if len(name) > 100:
        name = name[:100]
    if not name:
        name = "root"
    return name

def get_response_extension(content_type):
    """Get appropriate file extension based on content type"""
    if not content_type:
        return ".txt"

    content_type = content_type.lower().split(';')[0].strip()

    extension_map = {{
        'application/json': '.json',
        'application/ld+json': '.json',
        'text/json': '.json',
        'text/html': '.html',
        'application/xhtml+xml': '.html',
        'application/xml': '.xml',
        'text/xml': '.xml',
        'text/plain': '.txt',
        'text/csv': '.csv',
        'text/css': '.css',
        'text/javascript': '.js',
        'application/javascript': '.js',
        'application/x-javascript': '.js',
        'image/png': '.png',
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg',
        'image/gif': '.gif',
        'image/svg+xml': '.svg',
        'image/webp': '.webp',
        'application/pdf': '.pdf',
        'application/zip': '.zip',
        'font/woff': '.woff',
        'font/woff2': '.woff2',
        'application/octet-stream': '.bin',
    }}

    return extension_map.get(content_type, '.txt')

def generate_httpie_command(flow):
    """Generate httpie command string"""
    method = flow.request.method.upper()
    url = flow.request.pretty_url

    if method == "GET":
        cmd_parts = ["http"]
    else:
        cmd_parts = ["http", method]

    cmd_parts.append(url)

    skip_headers = {{'host', 'content-length', 'connection', 'accept-encoding',
                     'cache-control', 'pragma', 'upgrade-insecure-requests'}}

    for name, value in flow.request.headers.items():
        if name.lower() not in skip_headers:
            escaped_value = value.replace('\\"', '\\\\\\"')
            cmd_parts.append(f'{{name}}:"{{escaped_value}}"')

    if method in ["POST", "PUT", "PATCH"] and flow.request.content:
        try:
            body_text = flow.request.get_text()
            try:
                body_json = json.loads(body_text)
                json_str = json.dumps(body_json, separators=(',', ':'))
                cmd_parts.append(f"'{{json_str}}'")
            except json.JSONDecodeError:
                escaped_body = body_text.replace("'", "'\\"\\'\\"\\'")
                cmd_parts.append(f"'{{escaped_body}}'")
        except:
            cmd_parts.append("# <binary data - see original capture>")

    return " \\\\\\n  ".join(cmd_parts)

def response(flow):
    global flow_count, domain_counters
    flow_count += 1

    # Skip non-HTTP flows
    if not hasattr(flow, 'request') or not hasattr(flow, 'response'):
        return

    # Skip if no response
    if not flow.response:
        return

    # Get domain and create directory
    domain = flow.request.pretty_host
    domain_dir = output_dir / sanitize_path_name(domain)
    domain_dir.mkdir(exist_ok=True)

    # Create unique call directory name
    path = flow.request.path
    method = flow.request.method
    safe_path = sanitize_path_name(path)

    # Handle duplicates by adding counter
    base_call_name = f"{{method.lower()}}_{{safe_path}}"
    if domain not in domain_counters:
        domain_counters[domain] = {{}}

    if base_call_name in domain_counters[domain]:
        domain_counters[domain][base_call_name] += 1
        call_name = f"{{base_call_name}}_{{domain_counters[domain][base_call_name]}}"
    else:
        domain_counters[domain][base_call_name] = 0
        call_name = base_call_name

    call_dir = domain_dir / call_name
    call_dir.mkdir(exist_ok=True)

    # Generate httpie command
    httpie_cmd = generate_httpie_command(flow)

    # Write request file
    request_file = call_dir / "request"
    with open(request_file, 'w') as f:
        f.write("#!/bin/bash\\n")
        f.write("# HTTPie command to reproduce this request\\n")
        f.write(f"# Original URL: {{flow.request.pretty_url}}\\n")
        f.write(f"# Method: {{flow.request.method}}\\n")
        f.write(f"# Status: {{flow.response.status_code}}\\n")
        f.write("\\n")
        f.write(httpie_cmd)
        f.write("\\n")

    # Make request file executable
    request_file.chmod(request_file.stat().st_mode | stat.S_IEXEC)

    # Determine response file extension
    content_type = flow.response.headers.get('content-type', '')
    extension = get_response_extension(content_type)
    response_file = call_dir / f"response{{extension}}"

    # Write response file
    if flow.response.content:
        try:
            response_text = flow.response.get_text()

            if 'json' in content_type.lower():
                # Pretty-format JSON
                try:
                    response_json = json.loads(response_text)
                    with open(response_file, 'w') as f:
                        json.dump(response_json, f, indent=2)
                except json.JSONDecodeError:
                    # Invalid JSON, save as text
                    with open(response_file, 'w') as f:
                        f.write(response_text)
            else:
                # Non-JSON response
                with open(response_file, 'w') as f:
                    f.write(response_text)

        except Exception as e:
            # Error reading response - save error info
            with open(response_file, 'w') as f:
                f.write(f"Error reading response: {{e}}\\n")
                f.write(f"Content-Type: {{content_type}}\\n")
                f.write(f"Content-Length: {{len(flow.response.content)}} bytes")
    else:
        # Empty response
        with open(response_file, 'w') as f:
            f.write(f"# Empty response ({{flow.response.status_code}})\\n")

    print(f"📁 {{domain}}/{{call_name}} - {{flow.request.method}} {{flow.request.path}} -> {{flow.response.status_code}} ({{extension}})")
'''

    def show_tree_structure(self, path: Path, max_depth: int = 3, current_depth: int = 0):
        """Show directory tree structure."""
        if current_depth >= max_depth:
            return

        try:
            items = sorted(path.iterdir())
            dirs = [item for item in items if item.is_dir()]
            files = [item for item in items if item.is_file()]

            # Show directories first
            for i, dir_item in enumerate(dirs[:10]):  # Limit to 10 dirs
                prefix = "├── " if i < len(dirs) - 1 or files else "└── "
                print(f"{'  ' * current_depth}{prefix}{dir_item.name}/")

                if current_depth < max_depth - 1:
                    self.show_tree_structure(dir_item, max_depth, current_depth + 1)

            # Show some files
            for i, file_item in enumerate(files[:5]):  # Limit to 5 files
                prefix = "├── " if i < len(files) - 1 else "└── "
                print(f"{'  ' * current_depth}{prefix}{file_item.name}")

            if len(dirs) > 10:
                print(f"{'  ' * current_depth}... and {len(dirs) - 10} more directories")
            if len(files) > 5:
                print(f"{'  ' * current_depth}... and {len(files) - 5} more files")

        except PermissionError:
            pass
