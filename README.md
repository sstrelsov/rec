# rec

Record HTTP traffic for a domain.

```bash
pip install -e .
rec on nytimes.com
```

## Commands

```
rec on [domain]   Start recording
rec off           Stop recording
rec view          Show captures
rec status        Check if recording
rec clear         Remove all recordings
```

## Setup

Requires macOS and mitmproxy:

```bash
brew install mitmproxy
```

On first use, install the mitmproxy CA cert — run `rec on`, visit [mitm.it](http://mitm.it), and trust the cert in Keychain Access.
