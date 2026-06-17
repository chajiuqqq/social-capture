---
name: social-capture
description: "Capture post metadata and media from Xiaohongshu (小红书) or X/Twitter links and submit to secret-collector backend. Triggers when user shares a social media link and asks to save, capture, grab, or collect the post."
---

# Social Capture

Capture social media post metadata and media from Xiaohongshu or X/Twitter, and submit to secret-collector backend.

## Prerequisites

- secret-collector backend running at `http://localhost:8080` (see TOOLS.md for deploy details)
- Proxy for X/Twitter access (scripts read `HTTPS_PROXY` env, default: `http://192.168.39.240:7890`)
- yt-dlp available for video downloads (X and Xiaohongshu)

## Workflow

1. **Detect platform** — `xiaohongshu.com` or `x.com`/`twitter.com`
2. **Extract post data** — Run the platform-specific script
3. **Submit to backend** — POST to `/api/posts` with the extracted JSON
4. **Verify** — Check the post was saved (duplicate = already exists, HTTP 200)

## Platform Scripts

### Xiaohongshu (小红书)

```bash
python3 skills/social-capture/scripts/xhs_capture.py "<FULL_URL>"
```

The URL **must** include `xsec_token` and `xsec_source` parameters.

Returns JSON with author, content, images. For video posts, downloads via yt-dlp and includes local file path. Submit directly to backend.

### X/Twitter

```bash
python3 skills/social-capture/scripts/x_capture.py "<TWEET_URL>"
```

Requires proxy. Returns JSON with text content, images (`:large` suffix), author info. For video tweets, downloads via yt-dlp and includes local file path.

## Backend Submission

```bash
curl -s -X POST http://localhost:8080/api/posts \
  -H "Content-Type: application/json" \
  -d "$(python3 skills/social-capture/scripts/xhs_capture.py "<URL>")"
```

Response `{"duplicated": true}` = already saved (not an error). Media downloads are async (`pending` → `downloaded`).

For API schema and verification commands, see [references/api.md](references/api.md).
