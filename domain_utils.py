#!/usr/bin/env python3
"""
domain_utils.py - Domain parsing and grouping utilities

Provides functions to extract root domains from URLs and group subdomains
under their parent domains for better organization in timeline and API docs.
"""

import re
from urllib.parse import urlparse
from typing import Optional


def extract_root_domain(hostname: str) -> str:
    """
    Extract the root domain from a hostname.
    
    Examples:
    - api.example.com -> example.com
    - graphql.nytimes.com -> nytimes.com
    - subdomain.service.example.co.uk -> example.co.uk
    - localhost -> localhost
    - 192.168.1.1 -> 192.168.1.1
    
    Args:
        hostname: The hostname to extract root domain from
        
    Returns:
        The root domain string
    """
    if not hostname:
        return hostname
    
    hostname = hostname.lower().strip()
    
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
            # Return domain.tld.suffix (e.g., example.co.uk)
            if len(parts) >= 3:
                return f"{parts[-3]}.{parts[-2]}.{parts[-1]}"
            else:
                return hostname
    
    # Standard case: return the last two parts (domain.tld)
    if len(parts) >= 2:
        return f"{parts[-2]}.{parts[-1]}"
    
    return hostname


def _is_ip_address(hostname: str) -> bool:
    """Check if hostname is an IP address (IPv4 or IPv6)."""
    # Simple IPv4 check
    ipv4_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
    if ipv4_pattern.match(hostname):
        return True
    
    # Simple IPv6 check (basic patterns)
    if ':' in hostname and (hostname.count(':') >= 2 or '::' in hostname):
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
        # Remove the root domain from the end to get subdomain
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