# Backend API Reference

## Submit Post

**Endpoint:** `POST http://localhost:8080/api/posts`

### Request Schema

```json
{
  "platform": "xiaohongshu",
  "original_url": "https://www.xiaohongshu.com/explore/<noteId>",
  "author_name": "作者昵称",
  "author_avatar_url": "https://...",
  "content": "帖子正文（标题+描述）",
  "posted_at": "2026-06-13T14:40:11+08:00",
  "media": [
    {"kind": "image", "url": "https://ci.xiaohongshu.com/..."},
    {"kind": "video", "url": "/tmp/x_video.mp4"}
  ]
}
```

### Field Notes

| Field | Required | Notes |
|-------|----------|-------|
| `platform` | Yes | `"xiaohongshu"` or `"x"` |
| `original_url` | Yes | Deduplication key. Use canonical form: `https://www.xiaohongshu.com/explore/<noteId>` or `https://x.com/<user>/status/<tweetId>` |
| `author_name` | Yes | Display name |
| `author_avatar_url` | No | Avatar image URL |
| `content` | No | Post text (title + description for XHS) |
| `posted_at` | No | ISO 8601 format |
| `media` | No | Array of `{"kind":"image"|"video", "url":"..."}` |

### Responses

- **200 Created** — `{"id": <int>, ...}`
- **200 Duplicate** — `{"duplicated": true}` (same `original_url`)
- **400 Bad Request** — Invalid JSON or missing fields

### Media URL Handling

- `xhscdn.com` URLs automatically get `Referer: https://www.xiaohongshu.com/` header applied by backend
- X/Twitter images: always append `:large` suffix for full resolution
- Local file paths (e.g., `/tmp/x_video.mp4`) are auto-detected and uploaded by backend

## Verify Post

### List recent posts

```bash
curl -s "http://localhost:8080/api/posts?limit=3" | python3 -m json.tool | head -60
```

### Check media download status

```bash
curl -s "http://localhost:8080/api/posts?limit=1" | python3 -c "
import sys,json; d=json.load(sys.stdin)['posts'][0]
print(f'ID:{d[\"id\"]} author:{d[\"author_name\"]}')
for m in d['media']: print(f'  {m[\"position\"]}: {m[\"status\"]} {m.get(\"content_type\",\"\")}')
"
```

Media status transitions: `pending` → `downloaded` (may take a few seconds).
