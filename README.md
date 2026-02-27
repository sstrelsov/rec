# rec

Record and inspect HTTP traffic for a domain.

## Install

```bash
brew install sstrelsov/tap/rec
```

Or clone and run directly:

```bash
git clone https://github.com/sstrelsov/rec.git
cd rec
pip install -r requirements.txt
```

## Usage

```bash
rec on nytimes.com    # Start recording, filtered to nytimes.com
rec on              # Start recording ALL traffic
rec off             # Stop recording
rec view            # Show capture directories
rec status          # Check if recording
```

## How it works

`rec` uses [mitmproxy](https://mitmproxy.org/) to capture HTTP/HTTPS traffic through a local proxy. When you run `rec on`, it:

1. Enables the macOS system proxy
2. Starts `mitmdump` with traffic recording addons
3. Saves captures to `~/.rec/<domain>/`

When you run `rec off`, it stops the proxy and restores normal networking.

## Output structure

```
~/.rec/
  nytimes.com/                            # Domain-scoped captures
    capture_20260226_143015.mitm          # Raw mitmproxy dump
    nytimes.com/                          # Recorded calls by root domain
      get_landing-page_..._001/
        request.json
        response.json
        auth.txt
      metadata.json
  all/                                    # Unfiltered captures (rec on)
    capture_20260226_150000.mitm
    ...
```

Each recorded call includes:
- **request.json** - Method, URL, headers, body (auth tokens replaced with `{{auth_token}}`)
- **response.json** - Response body in native format (JSON, XML, HTML, or text)
- **auth.txt** - Extracted authentication token
- **metadata.json** - Domain-level stats and endpoint summary

## Configuration

Optional config at `~/.rec/config.toml`:

```toml
[filtering]
http_methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]
filter_static_assets = true
filter_browser_housekeeping = true

blocked_patterns = [
    "google-analytics.com",
    "facebook.net",
]
```

See the shipped `config.toml` for all options.

## Certificate setup

On first use, install the mitmproxy CA certificate:

1. Run `rec on` to start the proxy
2. Visit [http://mitm.it](http://mitm.it) in your browser
3. Download and install the certificate for your OS
4. Trust the certificate in Keychain Access (macOS)

## Requirements

- macOS (uses `networksetup` for proxy control)
- Python 3.11+
- mitmproxy (`brew install mitmproxy`)
