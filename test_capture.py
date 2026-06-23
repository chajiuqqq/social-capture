#!/usr/bin/env python3
"""Integration tests for social-capture skill scripts.

Runs xhs_capture.py and x_capture.py against real URLs from the local
capture-postgres database, validates output JSON structure, and optionally
submits to the backend.

Usage:
  HTTPS_PROXY="" python3 test_capture.py                    # all tests
  HTTPS_PROXY="" python3 test_capture.py --platform xhs      # XHS only
  HTTPS_PROXY="" python3 test_capture.py --platform x         # X only
  HTTPS_PROXY="" python3 test_capture.py --submit             # also POST to backend
"""

import json
import os
import subprocess
import sys
import urllib.request

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
BACKEND = os.environ.get("BACKEND_URL", "http://localhost:8080")
PROXY = os.environ.get("HTTPS_PROXY", os.environ.get("https_proxy", ""))

# ── Test cases from capture-postgres (idempotent — backend deduplicates) ──

XHS_TESTS = [
    {
        "name": "图文帖-4图 (id=16)",
        "url": "http://xhslink.com/o/1IXv4Cv7xRb",
        "expect": {"platform": "xiaohongshu", "has_media": True, "has_content": True},
    },
]

X_TESTS = [
    {
        "name": "图文帖-1图 buling_kira (id=8)",
        "url": "https://x.com/buling_kira/status/2065063470329201114",
        "expect": {"platform": "x", "has_media": True, "has_content": True},
    },
    {
        "name": "图文帖-1图 nya_Echo (id=13)",
        "url": "https://x.com/nya_Echo/status/2066513038375870686",
        "expect": {"platform": "x", "has_media": True, "has_content": True},
    },
]

# ── helpers ──

def run_script(script_name, url, extra_env=None):
    """Run a capture script, return (stdout, stderr, returncode)."""
    env = os.environ.copy()
    env.setdefault("HTTPS_PROXY", "")
    env.setdefault("https_proxy", "")
    if extra_env:
        env.update(extra_env)
    script = os.path.join(SCRIPTS_DIR, script_name)
    proc = subprocess.run(
        [sys.executable, script, url],
        capture_output=True, text=True, timeout=30, env=env,
    )
    return proc.stdout.strip(), proc.stderr.strip(), proc.returncode


def validate_json(raw, expected):
    """Validate capture output JSON against expected shape. Returns (ok, detail)."""
    if not raw:
        return False, "empty output"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return False, f"invalid JSON: {e}"
    for key, val in expected.items():
        if key == "has_media":
            media = data.get("media", [])
            if bool(val) and not media:
                return False, "expected media, got none"
            if not bool(val) and media:
                return False, f"expected no media, got {len(media)}"
        elif key == "has_content":
            content = data.get("content", "")
            if bool(val) and not content.strip():
                return False, "expected content, got empty"
        elif key == "has_author":
            if bool(val) and not data.get("author_name"):
                return False, "expected author_name"
        else:
            if data.get(key) != val:
                return False, f"field '{key}' expected '{val}', got '{data.get(key)}'"
    return True, f"platform={data.get('platform')} media={len(data.get('media',[]))}"


def submit_to_backend(json_str):
    """POST capture output to backend. Returns response body dict."""
    req = urllib.request.Request(
        f"{BACKEND}/api/posts",
        data=json_str.encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def check_backend_health():
    try:
        with urllib.request.urlopen(f"{BACKEND}/healthz", timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


# ── main ──

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Integration tests for social-capture")
    parser.add_argument("--platform", choices=["xhs", "x"], help="Only run tests for one platform")
    parser.add_argument("--submit", action="store_true", help="Also POST results to backend")
    args = parser.parse_args()

    tests = []
    if args.platform in (None, "xhs"):
        tests.extend([("xhs", t) for t in XHS_TESTS])
    if args.platform in (None, "x"):
        tests.extend([("x", t) for t in X_TESTS])

    script_map = {"xhs": "xhs_capture.py", "x": "x_capture.py"}

    backend_ok = check_backend_health()
    if args.submit and not backend_ok:
        print(f"WARNING: backend at {BACKEND} is not reachable\n")

    passed = failed = 0
    for platform, t in tests:
        label = f"[{platform.upper()}] {t['name']}"
        print(f"  {label} ... ", end="", flush=True)

        stdout, stderr, rc = run_script(script_map[platform], t["url"])
        if rc != 0:
            print(f"FAIL (exit={rc})")
            print(f"    stderr: {stderr[:200]}")
            failed += 1
            continue

        ok, detail = validate_json(stdout, t["expect"])
        if not ok:
            print(f"FAIL ({detail})")
            print(f"    stdout: {stdout[:200]}")
            failed += 1
            continue

        print(f"OK ({detail})", end="")

        if args.submit and backend_ok:
            try:
                resp = submit_to_backend(stdout)
                dup = "(duplicate)" if resp.get("duplicated") else f"(id={resp.get('id')})"
                print(f" → POST {dup}", end="")
            except Exception as e:
                print(f" → POST error: {e}", end="")

        print()
        passed += 1

    print(f"\n{passed} passed, {failed} failed")

    # Quick cross-check with backend
    if backend_ok:
        try:
            with urllib.request.urlopen(f"{BACKEND}/api/posts?limit=3") as resp:
                recent = json.loads(resp.read())
            print("\nRecent posts in backend:")
            for p in recent.get("posts", []):
                media = [f"{m['kind']}/{m['status']}" for m in p.get("media", [])]
                print(f"  id={p['id']} {p['platform']:>12}  {p['author_name'][:16]:<16}  media=[{', '.join(media)}]")
        except Exception:
            pass

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
