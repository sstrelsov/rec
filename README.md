# Henry the Navigator - Network Traffic Analysis Tool

A professional Python-based network traffic capture and analysis system using mitmproxy. Henry the Navigator charts uncharted digital waters by automatically generating comprehensive API documentation, interactive timelines, and real-time traffic analysis from browser sessions.

## Quick Start

```bash
# Start traffic capture with automatic analysis
make run

# Browse normally - all traffic is captured automatically

# Stop capture and generate comprehensive reports
make stop

# View results
make viewer       # Interactive API documentation (Swagger UI)
make open-timeline # Chronological timeline of API calls
make view         # Browse organized results by domain
```

**Complete documentation:** See [addons.md](addons.md) for enhanced features reference.

## Installation

```bash
# Install mitmproxy
brew install mitmproxy

# Install certificate (one-time setup)
make run
# Visit http://mitm.it in your browser to download and install certificate
# Then stop: make stop
```

## Commands

| Command | Description |
|---------|-------------|
| `make run` | Start enhanced capture with API documentation and timeline generation |
| `make stop` | Stop capture and auto-generate all reports |
| `make viewer` | Open interactive API documentation (Swagger UI) |
| `make open-timeline` | Open chronological timeline of API calls |
| `make view` | Browse organized results by domain |
| `make config` | Show current configuration |
| `make status` | Check current capture status |
| `make basic` | Run in basic mode (no enhanced features) |
| `make clean` | Remove all output files |

## Core Features

### Traffic Organization
- **Domain-based structure**: APIs automatically organized by base domain
- **Executable commands**: Each request saved as HTTPie command for replay
- **Zero configuration**: Works immediately with sensible defaults
- **Clean workflow**: Simple commands handle complete capture-to-analysis pipeline

### Enhanced Analysis
- **OpenAPI documentation**: Auto-generates professional Swagger specifications from live traffic
- **Interactive timeline**: Chronological visualization of all API interactions
- **Real-time monitoring**: Live analysis with performance insights during capture
- **Smart filtering**: Automatically excludes advertising and analytics noise
- **Professional output**: Documentation quality that rivals official API specifications

## Output Structure

Henry organizes captured traffic into a clear hierarchy:

- **Domain-separated API calls** in individual directories
- **Executable HTTPie commands** for request reproduction
- **Complete JSON responses** for analysis
- **Smart filtering** by domain, HTTP method, and response status
- **Traffic summaries** with timing and payload size data

## Example Session

```bash
# Analyze Airbnb's API structure
make run
# Navigate Airbnb.com normally...
make stop

# Generated structure:
# output/
# └── airbnb.com/
#     ├── get_stayspdpsections_token_2025-08-02_21-51-05_008/
#     │   ├── request.json    # HTTPie command
#     │   ├── response.json   # API response
#     │   ├── auth.txt        # Authentication details
#     │   └── metadata.json   # Request metadata
#     └── post_authenticate_2025-08-02_21-50-12_003/
#         ├── request.json
#         └── response.json

make view
# Organized APIs: output/
# Found 47 API calls across 3 domains:
#   airbnb.com: 23 calls
#   api.openai.com: 12 calls
#   github.com: 12 calls
```

## Advanced Usage

```bash
# Direct Python interface
python mitmtool.py run --output custom.mitm
python mitmtool.py view --input custom.mitm --domain airbnb
python mitmtool.py organize --input custom.mitm --output my_analysis

# Domain-specific filtering
python mitmtool.py view --domain api.openai.com
```

## Configuration

Customize behavior by editing the configuration file:

```bash
# Primary settings in config.toml
OUTPUT_DIR=output
VIEWER_PORT=8000
```

View current configuration: `make config`

## Architecture

```
mitmtool.py        # Main CLI interface
├── config.py        # Configuration management (TOML-based)
├── proxy_manager.py # macOS proxy system control
├── capture.py       # Traffic capture and organization
├── parser.py        # Flow parsing and analysis
├── generate_reports.py # Enhanced reporting system
└── makefile         # Workflow automation
```

## Security Considerations

- **Comprehensive capture**: Records ALL browser traffic including sensitive data
- **Session management**: Always execute `make stop` when analysis complete
- **Certificate management**: Monitor for certificate warnings in browser
- **Isolation recommended**: Consider using dedicated browser profiles for analysis

---

**Certificate installation:** http://mitm.it  
**Help and documentation:** `make help`
