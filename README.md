# 🕵️ mitmtool - Elegant Network Traffic Capture

A streamlined Python tool for capturing and analyzing network traffic using mitmproxy. **Now with enhanced features** including automatic OpenAPI documentation, interactive timelines, and real-time analysis!

## 🚀 Quick Start

```bash
# 1. Start enhanced capturing (proxy + capture + analysis)
make run          # ✨ NEW: Includes API docs + timeline + filtering

# 2. Browse normally - all traffic is captured automatically

# 3. Stop and auto-generate all reports
make stop         # ✨ NEW: Auto-generates OpenAPI docs + timeline

# 4. View results (multiple options now!)
make viewer       # 🚀 Interactive API documentation (Swagger UI)
make open-timeline# 🕒 Chronological timeline of API calls
make view         # 📁 Browse organized results (original)
```

> 📖 **Complete guide:** See [addons.md](addons.md) for full enhanced features documentation

## 📦 Installation

```bash
# Install mitmproxy
brew install mitmproxy

# Install certificate (one-time setup)
make run
# Visit http://mitm.it in your browser → Download & install certificate
# Then stop: make stop
```

## 🛠️ Commands

| Command | Description |
|---------|-------------|
| `make run` | ✨ Enhanced capture (API docs + timeline + analysis) |
| `make stop` | Stop capture & auto-generate all reports |
| `make viewer` | 🚀 Interactive API documentation (Swagger UI) |
| `make open-timeline` | 🕒 Chronological timeline of API calls |
| `make view` | 📁 Browse organized results (original) |
| `make status` | Check current status |
| `make basic` | 🔧 Run in basic mode (no enhancements) |
| `make clean` | Remove all files |

## 💡 What Makes This Elegant

### Core Elegance
- **Unified commands**: `make run` handles proxy + capture automatically
- **Smart organization**: APIs organized by domain with executable commands
- **Zero configuration**: Works out of the box with sensible defaults
- **Clean interface**: Simple commands for the complete workflow

### ✨ Enhanced Features (NEW!)
- **📚 OpenAPI documentation**: Auto-generates Swagger specs from live traffic
- **🕒 Interactive timeline**: Chronological visualization of API interactions
- **📊 Real-time analysis**: Live monitoring with performance insights
- **🚫 Smart filtering**: Automatically blocks ads/analytics noise
- **🎯 Professional output**: Documentation that rivals official API docs

## 📊 What You Get

- **Organized API calls** in separate directories
- **Executable HTTPie commands** for each request
- **JSON responses** saved for analysis
- **Smart filtering** by domain, method, status
- **Traffic summaries** with timing and size data

## 🔍 Example Workflow

```bash
# Capture AirDNA traffic
make run
# Browse AirDNA.co normally...
make stop

# Results:
# api_calls_20250102_143022/
# ├── get_api_airdna_co_v1_search/
# │   ├── request      # HTTPie command
# │   └── response.json
# ├── post_api_airdna_co_v1_analyze/
# │   ├── request
# │   └── response.json
# └── ...

make view
# 📂 Organized APIs: api_calls_20250102_143022
# Found 23 API calls:
#   get_api_airdna_co_v1_search
#   post_api_airdna_co_v1_analyze
#   ...
```

## 🎯 Advanced Usage

```bash
# Python interface (if needed)
python mitmtool.py run --output custom.mitm
python mitmtool.py view --input custom.mitm --domain airdna
python mitmtool.py organize --input custom.mitm --output my_apis

# Filter and search
python mitmtool.py view --domain api.openai.com
```

## 🔧 Architecture

```
mitmtool.py        # Main CLI entry point
├── proxy_manager.py # macOS proxy control
├── capture.py       # Traffic capture, viewing & organization
├── parser.py        # Flow parsing & analysis
└── makefile         # Simple workflow commands
```

## 🚨 Security Notes

- Captures ALL browser traffic including sensitive data
- Always run `make stop` when finished
- Be mindful of certificate warnings
- Use separate browser profiles for analysis

---

**🔗 Need the certificate?** → http://mitm.it
**❓ Need help?** → `make help`
