#!/usr/bin/env python3
"""
decompress_addon.py - Mitmproxy addon to ensure response decompression

This addon forces decompression of all response content during capture
to ensure we can properly read and organize the responses later.
"""

from mitmproxy import http
import logging

def response(flow: http.HTTPFlow) -> None:
    """Process responses to ensure they are decompressed."""
    if not flow.response:
        return

    url = flow.request.pretty_url if flow.request else "unknown"
    print(f"📦 Processing response for: {url}")

    try:
        # Check if we have content before decompression
        original_content = flow.response.content
        print(f"📏 Original content length: {len(original_content) if original_content else 0}")

        # Force decompression by accessing the content
        # This triggers mitmproxy's automatic decompression
        decompressed_content = flow.response.content
        print(f"📏 Decompressed content length: {len(decompressed_content) if decompressed_content else 0}")

        # Also try to get the text to ensure it's properly decoded
        if flow.response.content:
            try:
                text_content = flow.response.get_text()
                if text_content:
                    print(f"📄 Text content length: {len(text_content)}")
                    print(f"🔍 First 100 chars: {text_content[:100]}")
                else:
                    print("⚠️  get_text() returned None or empty")
            except Exception as e:
                print(f"⚠️  Text decoding failed: {e}")
                pass
        else:
            print("❌ No content in response")

    except Exception as e:
        # Log errors but don't fail the flow
        print(f"❌ Decompression error for {url}: {e}")
        pass
