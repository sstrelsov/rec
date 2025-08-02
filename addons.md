# 🚀 Enhanced MitmTool Addons Documentation

> **Transform your mitmproxy captures into powerful API documentation and analysis**

## 📋 Table of Contents

- [🎯 Overview](#-overview)
- [✨ Features](#-features)
- [🏗️ Architecture](#️-architecture)
- [📊 Addons Reference](#-addons-reference)
- [🚀 Quick Start](#-quick-start)
- [🎮 Usage Guide](#-usage-guide)
- [🔧 Configuration](#-configuration)
- [📁 Output Files](#-output-files)
- [🔍 Troubleshooting](#-troubleshooting)
- [💡 Advanced Usage](#-advanced-usage)

---

## 🎯 Overview

The Enhanced MitmTool system extends your basic mitmproxy capture with **three powerful addons** that automatically:

- 📚 **Generate OpenAPI documentation** from captured traffic
- 🕒 **Create interactive chronological timelines** of API calls
- 📊 **Provide real-time traffic analysis** during capture
- 🚫 **Filter out ads/analytics noise** automatically

**Zero configuration required** - just run `make run` and everything works!

---

## ✨ Features

### 🎯 **Smart Traffic Filtering**
- Automatically blocks 25+ ad/analytics patterns (Google Analytics, Facebook, etc.)
- Focuses on real API traffic you care about
- Configurable blocklist for custom filtering

### 📚 **Automatic API Documentation**
- Generates OpenAPI 3.0 specifications from live traffic
- Creates human-readable documentation
- Interactive Swagger UI viewer
- Supports multiple domains simultaneously

### 🕒 **Interactive Timeline Visualization**
- Chronological view of all API calls
- Filter by domain, method, status code
- Export as HTML, JSON, CSV, or Markdown
- Beautiful web interface

### 📊 **Real-time Traffic Analysis**
- Live statistics during capture
- Performance monitoring (slow requests, large responses)
- API endpoint discovery and categorization
- Method and status code distribution

---

## 🏗️ Architecture

```
mitmtool.py (CLI)
    ↓
capture.py (TrafficCapture)
    ↓
mitmdump + Enhanced Addons
    ├── 📊 TrafficAnalyzer     → Real-time stats
    ├── 📚 APIExtractor        → OpenAPI docs
    └── 🕒 APITimeline         → Timeline data

Output:
├── capture.mitm              → Raw capture file
├── api_calls_*/              → Organized calls (original)
├── api_docs/                 → OpenAPI documentation
│   ├── domain.com/
│   │   ├── openapi.json     → Swagger spec
│   │   └── README.md        → Human docs
│   └── viewer.html          → Interactive viewer
└── api_timeline/             → Timeline visualization
    ├── timeline.html        → Interactive timeline
    ├── timeline.json        → Raw data
    ├── timeline.csv         → Spreadsheet format
    └── timeline.md          → Text summary
```

---

## 📊 Addons Reference

### 1. 📊 **TrafficAnalyzer** (`addons/traffic_analyzer.py`)

**Purpose:** Real-time monitoring and analysis during capture

**Features:**
- Live traffic statistics every 50 requests
- Performance alerts for slow requests (>5s) and large responses (>1MB)
- Domain, method, and status code distribution
- API endpoint pattern detection
- Error pattern tracking

**Console Output Example:**
```
📊 TRAFFIC ANALYSIS REPORT (Flows: 150)
🌐 Top Domains:
  • api.example.com: 45 requests
  • cdn.example.com: 23 requests
⏱️  Response Times: Avg 245.3ms, Max 1205.7ms
📊 Status Codes:
  • 200: 142
  • 404: 6
  • 500: 2
🔗 Popular API Endpoints:
  • /api/v1/users/{id} [GET, PUT]: 23 calls
  • /api/v1/posts [GET, POST]: 18 calls
```

### 2. 📚 **APIExtractor** (`addons/api_extractor.py`)

**Purpose:** Automatic API documentation generation

**Features:**
- OpenAPI 3.0 specification generation
- Request/response schema inference
- Parameter extraction (path, query, headers, body)
- Example request/response capture
- Multi-domain support

**Generated Files:**
```
api_docs/
├── domain.com/
│   ├── openapi.json     # Full OpenAPI 3.0 spec
│   └── README.md        # Human-readable summary
└── viewer.html          # Interactive Swagger UI
```

**OpenAPI Spec Features:**
- Full endpoint documentation
- Parameter definitions with examples
- Response schemas with status codes
- Request body schemas for POST/PUT/PATCH
- Server definitions

### 3. 🕒 **APITimeline** (`addons/api_timeline.py`)

**Purpose:** Chronological visualization of API interactions

**Features:**
- Timeline of all API calls with timestamps
- Interactive HTML visualization
- Multiple export formats (HTML, JSON, CSV, MD)
- Filtering and search capabilities
- Request/response correlation

**Timeline Data:**
- Timestamp and duration
- HTTP method and URL
- Status codes and response sizes
- Request/response headers
- Domain categorization

---

## 🚀 Quick Start

### **Method 1: Enhanced Capture (Recommended)**
```bash
make run          # Start enhanced capture with all addons
# Browse normally...
make stop         # Auto-generates all reports

# View results:
make viewer       # Interactive API docs
make open-timeline # Timeline visualization
```

### **Method 2: Generate from Existing Captures**
```bash
# From any existing .mitm file:
python generate_reports.py your_capture.mitm

# Or from most recent:
make timeline
make docs
```

### **Method 3: Basic Mode (No Enhancements)**
```bash
make basic        # Original behavior without addons
```

---

## 🎮 Usage Guide

### **1. 📊 Viewing Interactive API Documentation**

```bash
# Start the documentation server:
make viewer
```

This opens `http://localhost:8000/viewer.html` with:
- **Dropdown selection** of all captured APIs
- **Full Swagger UI** with interactive testing
- **Try it out** functionality for each endpoint
- **Download OpenAPI specs** for import into other tools

### **2. 🕒 Exploring the Timeline**

```bash
# Open interactive timeline:
make open-timeline
```

Features:
- **Chronological view** of all API calls
- **Filter by domain, method, status**
- **Search functionality**
- **Request/response details** on click
- **Export options**

### **3. 📁 Working with Generated Files**

**OpenAPI Integration:**
```bash
# Import into Postman:
# File → Import → api_docs/domain.com/openapi.json

# Use with curl:
curl -X GET "https://api.example.com/v1/users/123" \
  -H "Authorization: Bearer TOKEN"

# Validate specs:
python -m json.tool api_docs/domain.com/openapi.json
```

**Timeline Data Analysis:**
```bash
# Open CSV in Excel/Google Sheets:
open api_timeline/timeline.csv

# Process JSON with jq:
cat api_timeline/timeline.json | jq '.[] | select(.status_code >= 400)'

# Read markdown summary:
cat api_timeline/timeline.md
```

---

## 🔧 Configuration

### **Addon Settings**

Addons support configuration through mitmproxy options. When running offline (with `generate_reports.py`), sensible defaults are used.

**TrafficAnalyzer Options:**
```python
traffic_analyzer_enabled = True           # Enable/disable addon
analyzer_alert_threshold = 5000          # Slow request threshold (ms)
analyzer_size_threshold = 1048576        # Large response threshold (bytes)
analyzer_report_interval = 50            # Print stats every N requests
```

**APIExtractor Options:**
```python
api_extractor_enabled = True             # Enable/disable addon
extractor_min_calls = 3                  # Minimum calls to document endpoint
extractor_example_limit = 3              # Max examples per endpoint
```

**APITimeline Options:**
```python
api_timeline_enabled = True              # Enable/disable addon
```

### **Customizing Ad/Analytics Blocking**

All three addons share the same blocklist. To customize, edit the `blocked_patterns` set in any addon:

```python
self.blocked_patterns = {
    # Analytics
    'google-analytics.com', 'mixpanel.com', 'segment.com',

    # Advertising
    'googlesyndication.com', 'doubleclick.net', 'facebook.com/tr',

    # Custom patterns
    'your-analytics-domain.com', '/internal/tracking'
}
```

### **Enhanced vs Basic Mode**

Control enhancement level via command line:

```bash
# Enhanced mode (default):
make run                    # All addons enabled
python mitmtool.py run      # All addons enabled

# Basic mode:
make basic                  # No addons
python mitmtool.py run --basic  # No addons
```

---

## 📁 Output Files

### **Directory Structure**
```
mitm/
└── output/                         # 📁 All outputs organized here
    ├── capture_TIMESTAMP.mitm      # Raw mitmproxy dump
    ├── api_calls_TIMESTAMP/        # Original organized structure
    ├── api_docs/                   # 📚 API Documentation
    │   ├── viewer.html             # Interactive viewer
    │   ├── domain1.com/
    │   │   ├── openapi.json       # OpenAPI 3.0 spec
    │   │   └── README.md          # Human-readable docs
    │   └── domain2.com/
    │       ├── openapi.json
    │       └── README.md
    └── api_timeline/               # 🕒 Timeline Visualization
        ├── timeline.html          # Interactive timeline
        ├── timeline.json          # Raw timeline data
        ├── timeline.csv           # Spreadsheet format
        └── timeline.md            # Text summary
```

### **File Descriptions**

**`output/api_docs/viewer.html`**
- Interactive Swagger UI viewer
- Dropdown to select different APIs
- Full documentation browser
- Requires local server to avoid CORS

**`output/api_docs/domain.com/openapi.json`**
- Complete OpenAPI 3.0 specification
- Import into Postman, Insomnia, etc.
- Use with code generators
- Validates with Swagger tools

**`output/api_docs/domain.com/README.md`**
- Human-readable API summary
- Endpoint list with call counts
- Parameter summaries
- Status code distributions

**`api_timeline/timeline.html`**
- Interactive chronological view
- Filter and search capabilities
- Click for request/response details
- Timeline scrubbing

**`api_timeline/timeline.json`**
- Raw timeline data
- Machine-readable format
- Process with scripts/tools
- Complete request/response info

---

## 🔍 Troubleshooting

### **Common Issues**

**❌ No API docs generated**
```bash
# Check if APIs were detected:
ls -la api_docs/

# If empty, try lowering the minimum calls threshold:
# Edit addons/api_extractor.py, change:
# extractor_min_calls = 1  # Instead of 3

# Regenerate:
python generate_reports.py your_capture.mitm
```

**❌ CORS errors in viewer**
```bash
# Always use the server instead of opening files directly:
make viewer                    # Starts local server
# NOT: open api_docs/viewer.html  # Will have CORS issues
```

**❌ Timeline empty**
```bash
# Check if API calls were captured:
ls -la api_timeline/

# Verify the capture has API traffic:
python parser.py your_capture.mitm --summary

# Try regenerating:
python generate_reports.py your_capture.mitm
```

**❌ Server port conflicts**
```bash
# If port 8000 is busy:
python serve_docs.py -p 8080   # Use different port
```

### **Debugging**

**Enable verbose logging:**
```bash
# Check what's being filtered:
grep -i "blocked" capture.log

# See addon loading:
head -20 capture.log

# Monitor real-time analysis:
tail -f capture.log | grep "TRAFFIC ANALYSIS"
```

**Validate generated files:**
```bash
# Check OpenAPI spec validity:
python -m json.tool api_docs/domain.com/openapi.json

# Count timeline entries:
cat api_timeline/timeline.json | jq '. | length'

# Check for specific domains:
find api_docs -name "*.json" | head -10
```

---

## 💡 Advanced Usage

### **Custom Filtering**

**Add custom blocked patterns:**
```python
# In any addon file, modify blocked_patterns:
self.blocked_patterns.add('your-tracking-domain.com')
self.blocked_patterns.add('/api/internal/metrics')
```

**Create domain-specific documentation:**
```bash
# Generate docs for specific domain only:
python generate_reports.py capture.mitm | grep "api.example.com"
```

### **Integration with CI/CD**

**Automated API documentation:**
```bash
#!/bin/bash
# ci-docs.sh - Auto-generate API docs from test runs

# Run your API tests through mitmproxy
make run &
PID=$!

# Run your test suite
npm test  # or pytest, etc.

# Stop capture and generate docs
kill $PID
make stop

# Upload docs to your documentation site
cp -r api_docs/* /path/to/doc-site/
```

### **Data Analysis with Timeline**

**Extract specific metrics:**
```bash
# Find slowest endpoints:
cat api_timeline/timeline.json | jq -r '.[] | select(.duration > 1000) | "\(.method) \(.url): \(.duration)ms"'

# Count calls by domain:
cat api_timeline/timeline.json | jq -r '.[].domain' | sort | uniq -c

# Find error patterns:
cat api_timeline/timeline.json | jq -r '.[] | select(.status_code >= 400) | "\(.status_code): \(.url)"'
```

### **Custom Report Generation**

**Create custom reports from timeline data:**
```python
# custom_analysis.py
import json

with open('api_timeline/timeline.json') as f:
    timeline = json.load(f)

# Analyze API usage patterns
domains = {}
for call in timeline:
    domain = call['domain']
    domains[domain] = domains.get(domain, 0) + 1

print("API Usage by Domain:")
for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True):
    print(f"  {domain}: {count} calls")
```

---

## 🎉 Summary

The Enhanced MitmTool addon system transforms basic traffic capture into a comprehensive API analysis platform:

✅ **Zero-config** - Works out of the box with `make run`
✅ **Smart filtering** - Removes ads/analytics noise automatically
✅ **Multiple outputs** - OpenAPI docs, timelines, real-time analysis
✅ **Professional quality** - Generate documentation that rivals official API docs
✅ **Integration ready** - Export to Postman, CI/CD, analysis tools

**Your API reverse engineering just got 10x more powerful!** 🚀

---

**Questions or issues?** Check the [troubleshooting section](#-troubleshooting) or run `make help` for quick commands.
