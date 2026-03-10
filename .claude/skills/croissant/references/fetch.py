#!/usr/bin/env python3
"""
Phase 1 page fetcher for the Croissant skill.

Usage:
  python3 references/fetch.py --links  <url>   # extract all href links (HTML only)
  python3 references/fetch.py --text   <url>   # strip HTML, print readable body text
  python3 references/fetch.py --both   <url>   # links then text (default if no flag given)
  python3 references/fetch.py --raw    <url>   # raw HTML/JS (use when inspecting page structure)
  python3 references/fetch.py --hrefs  <url>   # extract href/route strings from HTML or JS bundles

--hrefs works on both HTML pages and JavaScript bundles: it extracts every
string that looks like an internal path (/foo/bar) from href attributes,
href: assignments, and route definitions. Use this instead of writing an
inline Python script to grep a JS bundle.

Output always goes to stdout. Pipe through head/tail as needed.
"""

import sys
import re
import requests
from html.parser import HTMLParser

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href", "")
            if href:
                self.links.append(href)


def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
    print(f"# Status: {r.status_code}  Length: {len(r.text)}  URL: {r.url}", file=sys.stderr)
    return r.text


def extract_links(html):
    p = LinkParser()
    p.feed(html)
    return sorted(set(p.links))


def extract_hrefs(content):
    """Extract internal path strings from HTML or JS bundle content."""
    patterns = [
        r'href\s*[=:]\s*["\'](/[^\s"\'>,\)]+)',   # href="/foo" or href: '/foo'
        r'path\s*:\s*["\'](/[^\s"\'>,\)]+)',        # path: '/foo'
        r'to\s*:\s*["\'](/[^\s"\'>,\)]+)',          # to: '/foo'
        r'route\s*:\s*["\'](/[^\s"\'>,\)]+)',       # route: '/foo'
    ]
    found = set()
    for pat in patterns:
        found.update(re.findall(pat, content))
    return sorted(found)


def extract_text(html):
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&#?\w+;", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    mode = "--both"
    url = None
    for a in args:
        if a in ("--links", "--text", "--both", "--raw", "--hrefs"):
            mode = a
        else:
            url = a

    if not url:
        print("Error: no URL provided", file=sys.stderr)
        sys.exit(1)

    html = fetch(url)

    if mode == "--raw":
        print(html)
    elif mode == "--links":
        for link in extract_links(html):
            print(link)
    elif mode == "--hrefs":
        for href in extract_hrefs(html):
            print(href)
    elif mode == "--text":
        print(extract_text(html))
    else:  # --both
        print("=== LINKS ===")
        for link in extract_links(html):
            print(link)
        print("\n=== TEXT ===")
        print(extract_text(html))


if __name__ == "__main__":
    main()
