# 🕵️ mitmtool - macOS Proxy & Traffic Capture Tool

A Python-based system to programmatically control macOS proxy settings and capture/analyze browser network traffic using mitmproxy.

## 🚀 Quick Start

```bash
# 1. Enable proxy mode
python mitmtool.py enable

# 2. Start capturing traffic
python mitmtool.py capture

# 3. Use your browser normally (visit AirDNA, APIs, etc.)
# Press Ctrl+C to stop capture

# 4. Disable proxy mode
python mitmtool.py disable

# 5. View captured traffic
python mitmtool.py view
```

## 📋 Prerequisites

### Install mitmproxy
```bash
# Using Homebrew (recommended)
brew install mitmproxy

# Using pip
pip install mitmproxy
```

### Install mitmproxy Certificate (Required for HTTPS)
1. **Start mitmproxy first:**
   ```bash
   python mitmtool.py enable
   python mitmtool.py capture
   ```

2. **Install certificate:**
   - Visit `http://mitm.it` in your browser
   - Download and install the certificate for your browser
   - **Chrome/Safari:** Download → Open → Add to Keychain → Trust
   - **Firefox:** Download → Settings → Certificates → Import

3. **Stop and restart:**
   ```bash
   # Press Ctrl+C to stop
   python mitmtool.py disable
   ```

## 🛠️ Installation

1. **Download the tool:**
   ```bash
   mkdir mitmtool && cd mitmtool
   # Save mitmtool.py to this directory
   ```

2. **Make it executable:**
   ```bash
   chmod +x mitmtool.py
   ```

3. **Test it:**
   ```bash
   python mitmtool.py status
   ```

## 📖 Commands

### `enable` - Turn on proxy mode
```bash
python mitmtool.py enable
```
- Configures all network services to route through `127.0.0.1:8080`
- Your browser will send all traffic through mitmproxy

### `disable` - Turn off proxy mode
```bash
python mitmtool.py disable
```
- Restores normal browser traffic routing
- Always run this when done capturing

### `status` - Check proxy status
```bash
python mitmtool.py status
```
- Shows current proxy settings for all network services
- Helpful for debugging connectivity issues

### `capture` - Start traffic capture
```bash
# Basic capture
python mitmtool.py capture

# Custom output file
python mitmtool.py capture --output api_session.mitm

# Capture with live output
python mitmtool.py capture --output airdna_analysis.mitm
```
- Starts `mitmdump` to capture all network traffic
- Saves binary dump file for later analysis
- Press `Ctrl+C` to stop capture

### `view` - Analyze captured traffic
```bash
# View default capture file
python mitmtool.py view

# View specific file
python mitmtool.py view --input api_session.mitm

# Filter by domain
python mitmtool.py view --domain airdna.co
python mitmtool.py view --domain api.openai.com
```
- Parses dump files and shows human-readable traffic
- Groups requests by domain
- Shows JSON response previews for APIs

## 🎯 Real-World Examples

### Example 1: Capture AirDNA API Traffic
```bash
# Setup
python mitmtool.py enable
python mitmtool.py capture --output airdna_session.mitm

# Use AirDNA in browser normally
# Browse listings, search properties, etc.
# Press Ctrl+C when done

# Cleanup & Analysis
python mitmtool.py disable
python mitmtool.py view --input airdna_session.mitm --domain airdna
```

### Example 2: Debug API Integration
```bash
# Start capture
python mitmtool.py enable
python mitmtool.py capture --output debug_api.mitm

# Run your app or visit web app
# All API calls will be captured

# Stop and analyze
python mitmtool.py disable
python mitmtool.py view --input debug_api.mitm
```

### Example 3: Security Research
```bash
# Capture authentication flows
python mitmtool.py enable
python mitmtool.py capture --output auth_flow.mitm

# Login to target site
# Navigate through authenticated sections
# Ctrl+C to stop

python mitmtool.py disable
python mitmtool.py view --input auth_flow.mitm
```

## 📊 Sample Output

### Proxy Status
```
🔍 Checking proxy status...
🟢 Wi-Fi: ENABLED (127.0.0.1:8080)
🟢 USB 10/100/1000 LAN: ENABLED (127.0.0.1:8080)
```

### Traffic Capture
```
📖 Reading traffic dump: airdna_session.mitm
📊 Found 47 HTTP flows

🌐 Domains captured:
  • airdna.co: 23 requests
  • api.airdna.co: 15 requests
  • static.airdna.co: 9 requests

🔗 Flow #1
   Method: GET
   URL: https://api.airdna.co/v1/properties/search
   Status: 200
   Size: 15420 bytes
   Content-Type: application/json
   JSON Preview:
{
  "results": [
    {
      "property_id": "12345",
      "name": "Modern Downtown Apartment",
      "price": 150
    }
  ]
}
   Timestamp: 2025-08-02 14:30:15
```

## 🔧 Troubleshooting

### "mitmdump not found"
```bash
# Install mitmproxy
brew install mitmproxy

# Verify installation
mitmdump --version
```

### "SSL Certificate Error" in Browser
1. Make sure you've installed the mitmproxy certificate
2. Visit `http://mitm.it` (not https) to download certificate
3. In Chrome: Settings → Privacy → Manage Certificates → Import
4. Trust the certificate for SSL

### "No flows found" when viewing
- Make sure you captured traffic first with `python mitmtool.py capture`
- Check that the dump file exists and isn't empty
- Verify you browsed sites while proxy was enabled

### Traffic not being captured
1. Check proxy status: `python mitmtool.py status`
2. Restart your browser after enabling proxy
3. Make sure mitmdump is running (you'll see live output)

### Permission errors with networksetup
```bash
# May need sudo for some network services
sudo python mitmtool.py enable
```

## 🎛️ Advanced Usage

### Export specific data
```python
# Custom script to extract API responses
flows = tool.parse_mitm_dump("capture.mitm")
for flow in flows:
    if "api" in flow.get("url", ""):
        print(f"API: {flow['url']}")
        if flow.get("response_content"):
            # Save response to file
            with open(f"response_{flow['timestamp']}.json", "w") as f:
                f.write(flow["response_content"])
```

### Filter by HTTP method
```python
# Only show POST requests
flows = [f for f in flows if f.get("method") == "POST"]
```

### Extract authentication headers
```python
# Look for auth tokens
for flow in flows:
    headers = flow.get("request_headers", {})
    auth = headers.get("Authorization", headers.get("authorization"))
    if auth:
        print(f"Auth found: {auth}")
```

## 🔐 Security Notes

- This tool captures **ALL** browser traffic including sensitive data
- Dump files may contain passwords, tokens, and personal information
- Always run `disable` when finished to restore normal browsing
- Consider using separate browser profiles for analysis
- Be mindful of HTTPS certificate warnings

## 🤝 Contributing

Feel free to extend this tool with:
- Web UI for viewing captures
- Real-time traffic filtering
- Integration with other analysis tools
- Export formats (HAR, CSV, etc.)
- Automated report generation

## 📝 License

This tool is for educational and debugging purposes. Use responsibly and in compliance with applicable laws and terms of service.
