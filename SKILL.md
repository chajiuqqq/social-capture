---
name: social-capture
description: "Capture post metadata and media from Xiaohongshu (小红书) or X/Twitter links and submit to secret-collector backend. Triggers when user shares a social media link and asks to save, capture, grab, or collect the post."
---

# Social Capture

Capture social media post metadata and media from Xiaohongshu or X/Twitter, and submit to secret-collector backend.

## Prerequisites

- secret-collector backend running at `http://localhost:8080` (see TOOLS.md for deploy details)
- Proxy for X/Twitter access: `HTTPS_PROXY` or `https_proxy` env var (default: `http://127.0.0.1:7890`)
- yt-dlp available for video downloads

## Quick Start

```bash
# Xiaohongshu (short links work directly)
cd <workspace> && python3 skills/social-capture/scripts/xhs_capture.py "<URL>"

# X/Twitter (requires proxy)
HTTPS_PROXY=http://127.0.0.1:7890 python3 skills/social-capture/scripts/x_capture.py "<URL>"

# Submit to backend
curl -s -X POST http://localhost:8080/api/posts \
  -H "Content-Type: application/json" \
  -d "$(python3 skills/social-capture/scripts/xhs_capture.py "<URL>")"
```

## Workflow

1. **Detect platform** — `xiaohongshu.com`/`xhslink.com` or `x.com`/`twitter.com`
2. **Extract post data** — Run the platform-specific script
3. **Submit to backend** — POST to `/api/posts` with the extracted JSON
4. **Verify** — Check the post was saved (duplicate = already exists, HTTP 200)

## Platform Scripts

### Xiaohongshu (小红书)

```bash
python3 skills/social-capture/scripts/xhs_capture.py "<URL>"
```

Supports short links (`xhslink.com`) and full URLs (`xiaohongshu.com/explore/...`, `xiaohongshu.com/discovery/item/...`).

Returns JSON with author, content, images (for 图文 posts). For video posts (视频), downloads via yt-dlp.

**Video download requires cookies.** Set one of:
- `XHS_COOKIE_FILE` env var → path to cookies.txt
- `XHS_COOKIE_BROWSER` env var → browser name (e.g. `chrome`)

Without cookies, video posts only capture metadata (author, content, posted_at) but no video file.

### X/Twitter

```bash
HTTPS_PROXY=http://127.0.0.1:7890 python3 skills/social-capture/scripts/x_capture.py "<URL>"
```

Requires proxy. Returns JSON with text content, images (`:large` suffix), author info. For video tweets, downloads via yt-dlp and includes local file path.

## Backend Submission

```bash
curl -s -X POST http://localhost:8080/api/posts \
  -H "Content-Type: application/json" \
  -d "$(python3 skills/social-capture/scripts/xhs_capture.py "<URL>")"
```

Response `{"duplicated": true}` = already saved (not an error). Media downloads are async (`pending` → `downloaded`).

## Supported URL Formats

| Platform | Format | Example |
|----------|--------|---------|
| XHS Short | `http://xhslink.com/o/<id>` | `http://xhslink.com/o/1IXv4Cv7xRb` |
| XHS Explore | `https://www.xiaohongshu.com/explore/<noteId>` | auto-converted |
| XHS Discovery | `https://www.xiaohongshu.com/discovery/item/<id>?xsec_token=...` | auto-converted |
| X/Twitter | `https://x.com/<user>/status/<id>` | both supported |

## For XHS Video Download (Cookies)

The `chajiuqqq.cn` API does not provide direct video download URLs. For video posts, we use yt-dlp, which requires authentication cookies:

```bash
# Option 1: Export cookies from browser to file, then:
XHS_COOKIE_FILE=/path/to/xhs_cookies.txt python3 skills/social-capture/scripts/xhs_capture.py "<URL>"

# Option 2: Use browser cookies directly (if Chrome/Firefox is installed):
XHS_COOKIE_BROWSER=chrome python3 skills/social-capture/scripts/xhs_capture.py "<URL>"
```

For API schema and verification commands, see [references/api.md](references/api.md).
