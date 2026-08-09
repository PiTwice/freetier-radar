#!/usr/bin/env python3
"""Watch provider pricing pages for changes.

For every tool in data/tools.json this script downloads the pricing page,
strips it to plain text, hashes it, and compares against the snapshot from
the previous run (stored in snapshots/). Tools whose page changed are
listed so you can re-verify the entry by hand and bump its `verified` date.

Usage:
    python3 scripts/check_changes.py            # check all
    python3 scripts/check_changes.py vercel neon # check specific ids

First run just records snapshots. No third-party dependencies.
Recommended cadence: weekly (cron or GitHub Actions, see README).
"""
import hashlib
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "tools.json"
SNAP_DIR = ROOT / "snapshots"
UA = "Mozilla/5.0 (compatible; FreeTierRadar/1.0; +https://github.com/)"
TIMEOUT = 20


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        raw = r.read().decode("utf-8", errors="replace")
    # strip scripts/styles/tags, collapse whitespace -> stable-ish text
    raw = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = re.sub(r"\s+", " ", raw)
    # drop obvious noise that changes every request
    raw = re.sub(r"(csrf|nonce|token)[=:\"'][\w-]+", "", raw, flags=re.I)
    return raw.strip()


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(argv: list[str]) -> int:
    tools = json.loads(DATA.read_text(encoding="utf-8"))["tools"]
    only = set(argv)
    if only:
        tools = [t for t in tools if t["id"] in only]
    SNAP_DIR.mkdir(exist_ok=True)

    changed, new, errors = [], [], []
    for t in tools:
        snap_file = SNAP_DIR / f"{t['id']}.json"
        try:
            text = fetch_text(t["pricing_url"])
        except Exception as e:  # noqa: BLE001
            errors.append((t["id"], str(e)))
            continue
        h = digest(text)
        if snap_file.exists():
            prev = json.loads(snap_file.read_text(encoding="utf-8"))
            if prev["hash"] != h:
                changed.append(t["id"])
        else:
            new.append(t["id"])
        snap_file.write_text(
            json.dumps({"hash": h, "checked": time.strftime("%Y-%m-%d"), "url": t["pricing_url"], "chars": len(text)}, indent=2),
            encoding="utf-8",
        )
        time.sleep(1)  # be polite

    print(f"checked: {len(tools)}  changed: {len(changed)}  new: {len(new)}  errors: {len(errors)}")
    if changed:
        print("\nRE-VERIFY these entries (pricing page changed):")
        for tid in changed:
            print(f"  - {tid}")
    if errors:
        print("\nfetch errors (page may be JS-only or blocking bots — verify manually):")
        for tid, err in errors:
            print(f"  - {tid}: {err}")
    # exit code 2 signals "changes found" so CI can flag it
    return 2 if changed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
