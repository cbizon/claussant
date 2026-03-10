#!/usr/bin/env python3
"""
Phase 2 schema extractor for the Croissant skill.

Fetches a URL (with partial/range download where possible) and extracts
column headers, field names, or table schemas — without downloading the
whole file.

Usage:
  python3 references/extract.py <format> <url>

Formats:
  tsv        TSV/CSV direct URL — prints first line (column headers)
  tsv-zip    TSV/CSV inside a ZIP — prints first line of the first TSV/CSV entry
  sdf        SDF direct URL — prints property names from first record
  sdf-zip    SDF inside a ZIP — prints property names from first record
  mysql-zip  MySQL dump inside a ZIP — prints CREATE TABLE statements
  tar        TAR archive — lists first ~200 member filenames and sizes
  json       JSON file or API response — prints top-level keys

Exit codes:
  0  success
  1  blocked (401/403/CAPTCHA/wrong content-type) — mark as blocked
  2  usage error
"""

import sys
import io
import re
import struct
import zlib
import zipfile
import tarfile
import json
import hashlib
import urllib.request

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
MAX_ZIP_BYTES = 5_000_000
MAX_RANGE_BYTES = 65_536


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------

def fetch_range(url, max_bytes):
    """Fetch up to max_bytes from url using a Range request."""
    req = urllib.request.Request(
        url,
        headers={**HEADERS, "Range": f"bytes=0-{max_bytes - 1}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            status = r.status
            data = r.read(max_bytes)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            print(f"BLOCKED: HTTP {e.code}", file=sys.stderr)
            sys.exit(1)
        # Some servers reject Range; fall back to full fetch
        data = fetch_full(url, max_bytes)
        return data
    _check_blocked(status, data)
    return data


def fetch_full(url, max_bytes):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            status = r.status
            data = r.read(max_bytes)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            print(f"BLOCKED: HTTP {e.code}", file=sys.stderr)
            sys.exit(1)
        raise
    _check_blocked(status, data)
    return data


def _check_blocked(status, data):
    if status in (401, 403):
        print(f"BLOCKED: HTTP {status}", file=sys.stderr)
        sys.exit(1)
    # CAPTCHA / login page delivered as 200: HTML instead of binary
    if data[:5] in (b"<!DOC", b"<html", b"<HTML"):
        print("BLOCKED: server returned HTML (session gate or CAPTCHA)", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# ZIP helper — shared by tsv-zip, sdf-zip, mysql-zip
# ---------------------------------------------------------------------------

def unzip_first_entry(data, read_bytes=MAX_RANGE_BYTES):
    """
    Return raw bytes from the first non-MACOSX entry in a (possibly partial) ZIP.
    Uses standard zipfile on the fast path; falls back to local-file-header parsing.
    """
    # Fast path: full ZIP fits in data
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        name = next(n for n in z.namelist() if not n.startswith("__MACOSX"))
        print(f"File in ZIP: {name}", file=sys.stderr)
        return z.open(name).read(read_bytes)
    except Exception:
        pass

    # Slow path: parse local file header from partial stream
    if data[:4] != b"PK\x03\x04":
        print("ERROR: not a ZIP or download blocked", file=sys.stderr)
        sys.exit(1)
    compression = struct.unpack_from("<H", data, 8)[0]
    fname_len   = struct.unpack_from("<H", data, 26)[0]
    extra_len   = struct.unpack_from("<H", data, 28)[0]
    fname       = data[30:30 + fname_len].decode("utf-8", errors="replace")
    payload     = data[30 + fname_len + extra_len:]
    print(f"File in ZIP (partial): {fname}", file=sys.stderr)
    if compression == 0:      # stored
        return payload[:read_bytes]
    elif compression == 8:    # deflated
        d = zlib.decompressobj(-15)
        return d.decompress(payload, read_bytes)
    else:
        print(f"Unsupported ZIP compression method: {compression}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Format extractors
# ---------------------------------------------------------------------------

def do_tsv(url):
    data = fetch_range(url, 4096)
    line = data.split(b"\n")[0].decode("utf-8", errors="replace")
    print(line)


def do_tsv_zip(url):
    data = fetch_full(url, MAX_ZIP_BYTES)
    raw = unzip_first_entry(data, read_bytes=4096)
    line = raw.split(b"\n")[0].decode("utf-8", errors="replace")
    print(line)


def _sdf_props(text_bytes):
    props = []
    for line in text_bytes.decode("utf-8", errors="replace").splitlines():
        if line.strip() == "$$$$":
            break
        if line.startswith("> <"):
            props.append(line.strip()[3:-1])
    return props


def do_sdf(url):
    data = fetch_range(url, MAX_RANGE_BYTES)
    props = _sdf_props(data)
    print("\n".join(props))


def do_sdf_zip(url):
    data = fetch_full(url, MAX_ZIP_BYTES)
    raw = unzip_first_entry(data, read_bytes=MAX_RANGE_BYTES)
    props = _sdf_props(raw)
    print("\n".join(props))


def do_mysql_zip(url):
    data = fetch_full(url, MAX_ZIP_BYTES)
    raw = unzip_first_entry(data, read_bytes=MAX_RANGE_BYTES)
    text = raw.decode("utf-8", errors="replace")
    tables = re.findall(r"CREATE TABLE `?(\w+)`?", text)
    print("Tables:", tables)
    for m in re.finditer(r"(CREATE TABLE[^;]+;)", text, re.DOTALL):
        print(m.group(1)[:1000])
        print("---")


def do_tar(url):
    data = fetch_range(url, 102_400)
    try:
        with tarfile.open(fileobj=io.BytesIO(data)) as t:
            for m in t.getmembers()[:30]:
                print(m.name, m.size)
    except Exception as e:
        print(f"Note (expected for truncated TAR): {e}", file=sys.stderr)


def do_md5(url):
    """Stream the full file and compute its MD5 checksum."""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            status = r.status
            if status in (401, 403):
                print(f"BLOCKED: HTTP {status}", file=sys.stderr)
                sys.exit(1)
            h = hashlib.md5()
            total = 0
            while True:
                chunk = r.read(1 << 20)  # 1 MB chunks
                if not chunk:
                    break
                h.update(chunk)
                total += len(chunk)
            print(f"md5:{h.hexdigest()}  bytes:{total}")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            print(f"BLOCKED: HTTP {e.code}", file=sys.stderr)
            sys.exit(1)
        raise


def do_json(url):
    data = fetch_full(url, 1_000_000)
    try:
        d = json.loads(data)
        if isinstance(d, dict):
            for k in d.keys():
                print(k)
        elif isinstance(d, list) and d:
            for k in (d[0].keys() if isinstance(d[0], dict) else []):
                print(k)
        else:
            print(repr(d)[:500])
    except json.JSONDecodeError:
        # Response was truncated mid-record; extract key names via regex
        print("# Note: JSON truncated; keys extracted via regex", file=sys.stderr)
        text = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else data
        # Find first object and extract its keys
        keys = re.findall(r'"([^"]+)"\s*:', text[:200_000])
        seen = []
        for k in keys:
            if k not in seen:
                seen.append(k)
        for k in seen:
            print(k)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

FORMATS = {
    "tsv":       do_tsv,
    "tsv-zip":   do_tsv_zip,
    "sdf":       do_sdf,
    "sdf-zip":   do_sdf_zip,
    "mysql-zip": do_mysql_zip,
    "tar":       do_tar,
    "json":      do_json,
    "md5":       do_md5,
}

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in FORMATS:
        print(__doc__)
        sys.exit(2)
    fmt, url = sys.argv[1], sys.argv[2]
    print(f"# Extracting {fmt} from {url}", file=sys.stderr)
    FORMATS[fmt](url)

if __name__ == "__main__":
    main()
