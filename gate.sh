#!/usr/bin/env bash
# Gate wrapper for the digest agent (single token command: the sandbox allowlist matches it reliably).
exec python -m analyze.digest_gate "$@"
