#!/usr/bin/env python3
"""
domain_utils.py - Domain parsing and grouping utilities

Provides functions to extract root domains from URLs, match against target
domains, and group subdomains under their parent domains.
"""

import re
from urllib.parse import urlparse
from typing import List, Optional


def extract_root_domain(hostname: str) -> str:
    """
    Extract the root domain from a hostname.

    Examples:
    - api.example.com -> example.com
    - graphql.nytimes.com -> nytimes.com
    - subdomain.service.example.co.uk -> example.co.uk
    - localhost -> localhost
    - 192.168.1.1 -> 192.168.1.1
    - api.example.com:8080 -> example.com
    """
    if not hostname:
        return hostname

    hostname = hostname.lower().strip()

    # Strip port number
    if ':' in hostname and not _is_ip_v6(hostname):
        hostname = hostname.rsplit(':', 1)[0]

    # Handle IP addresses (IPv4 and IPv6)
    if _is_ip_address(hostname):
        return hostname

    # Handle localhost and local development domains
    if hostname in ['localhost', '127.0.0.1', '::1'] or hostname.endswith('.local'):
        return hostname

    # Split hostname into parts
    parts = hostname.split('.')

    # If less than 2 parts, return as-is (e.g., "localhost")
    if len(parts) < 2:
        return hostname

    # Handle common two-level TLDs (e.g., .co.uk, .com.au, .github.io)
    two_level_tlds = {
        'co.uk', 'com.au', 'co.jp', 'co.kr', 'co.nz', 'co.za',
        'github.io', 'herokuapp.com', 'netlify.app', 'vercel.app',
        'github.dev', 'gitpod.io', 'repl.co', 'glitch.me'
    }

    # Check if the last two parts form a two-level TLD
    if len(parts) >= 3:
        potential_tld = f"{parts[-2]}.{parts[-1]}"
        if potential_tld in two_level_tlds:
            return f"{parts[-3]}.{parts[-2]}.{parts[-1]}"

    # Standard case: return the last two parts (domain.tld)
    return f"{parts[-2]}.{parts[-1]}"


def _is_ip_v6(hostname: str) -> bool:
    """Check if hostname looks like IPv6 (contains multiple colons)."""
    return hostname.count(':') >= 2 or '::' in hostname


def _is_ip_address(hostname: str) -> bool:
    """Check if hostname is an IP address (IPv4 or IPv6)."""
    ipv4_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
    if ipv4_pattern.match(hostname):
        return True

    if _is_ip_v6(hostname):
        return True

    return False


def parse_domain_input(raw: str) -> str:
    """
    Parse user-provided domain input into a clean root domain.

    Handles:
    - Full URLs: https://api.nytimes.com/svc/search/ -> nytimes.com
    - Bare domains: nytimes.com -> nytimes.com
    - Domains with ports: nytimes.com:8080 -> nytimes.com
    - Subdomains: api.nytimes.com -> nytimes.com
    """
    raw = raw.strip()

    # If it looks like a URL (has scheme), parse it
    if '://' in raw:
        parsed = urlparse(raw)
        hostname = parsed.hostname or parsed.netloc
        if hostname:
            return extract_root_domain(hostname)

    # Otherwise treat as hostname (possibly with port)
    return extract_root_domain(raw)


def matches_target_domains(hostname: str, target_domains: List[str]) -> bool:
    """
    Check if a hostname matches any of the target domains.

    A hostname matches if its root domain equals a target domain's root domain.
    Empty target_domains list means match everything.

    Examples:
        matches_target_domains("api.nytimes.com", ["nytimes.com"]) -> True
        matches_target_domains("google.com", ["nytimes.com"]) -> False
        matches_target_domains("anything.com", []) -> True
    """
    if not target_domains:
        return True

    host_root = extract_root_domain(hostname)
    for target in target_domains:
        if host_root == extract_root_domain(target):
            return True
    return False


def get_domain_hierarchy(hostname: str) -> dict:
    """
    Get domain hierarchy information for grouping.

    Returns:
        Dict with 'root_domain', 'full_domain', and 'subdomain' info
    """
    root_domain = extract_root_domain(hostname)

    result = {
        'root_domain': root_domain,
        'full_domain': hostname,
        'is_subdomain': hostname != root_domain,
        'subdomain': None
    }

    # Extract subdomain if it exists
    if result['is_subdomain'] and not _is_ip_address(hostname):
        if hostname.endswith(f".{root_domain}"):
            subdomain = hostname[:-len(f".{root_domain}")]
            result['subdomain'] = subdomain

    return result


def group_domains_by_root(domains: list) -> dict:
    """
    Group a list of domains by their root domain.

    Args:
        domains: List of domain strings

    Returns:
        Dict mapping root domains to lists of full domains
    """
    grouped = {}

    for domain in domains:
        root = extract_root_domain(domain)
        if root not in grouped:
            grouped[root] = []
        if domain not in grouped[root]:
            grouped[root].append(domain)

    return grouped
