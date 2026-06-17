#!/usr/bin/env python3
"""Capture a Xiaohongshu post via xhs API and output JSON for secret-collector."""

import json
import os
import subprocess
import sys
import urllib.request

if len(sys.argv) < 2:
    print("Usage: xhs_capture.py <XHS_POST_URL>", file=sys.stderr)
    sys.exit(1)

INPUT_URL = sys.argv[1]
API_URL = "https://xhs.chajiuqqq.cn/xhs/detail"

# 1. Call xhs API
req_body = json.dumps({"url": INPUT_URL, "download": False}).encode()
req = urllib.request.Request(API_URL, data=req_body, headers={
    "Content-Type": "application/json",
    "Accept": "application/json",
})
with urllib.request.urlopen(req) as resp:
    result = json.loads(resp.read())

if result.get("code") != 0:
    print(f"API error: {result.get('msg', 'unknown')}", file=sys.stderr)
    sys.exit(1)

data = result["data"]

# 2. Extract fields
note_id = data.get("作品ID", data.get("note_id", ""))
author = data.get("作者昵称", "")
avatar = data.get("作者链接", "")
title = data.get("作品标题", "")
desc = data.get("作品描述", "")
post_type = data.get("作品类型", "")  # "图文" or "视频"
posted_raw = data.get("发布时间", "")  # "YYYY-MM-DD_HH:MM:SS"
media_urls = data.get("下载地址", [])

# Build content: title first, then description
content_parts = []
if title:
    content_parts.append(title)
if desc and desc != title:
    content_parts.append(desc)
content = "\n".join(content_parts)

# Convert posted_at
posted_at = ""
if posted_raw:
    # "YYYY-MM-DD_HH:MM:SS" -> ISO 8601
    date_part, time_part = posted_raw.split("_")
    posted_at = f"{date_part}T{time_part}+08:00"

def download_video(url, output_path="/tmp/xhs_video.mp4"):
    """Download video using yt-dlp."""
    cmd = [
        "yt-dlp", "--no-warnings", "--no-cache-dir",
        "--force-overwrites",
        "-f", "best",
        "-o", output_path,
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"yt-dlp warning: {result.stderr}", file=sys.stderr)
    return output_path


# Build media
media = []
if post_type == "视频":
    media.append({"kind": "video", "url": download_video(INPUT_URL)})
elif post_type == "图文" and media_urls:
    for url in media_urls:
        media.append({"kind": "image", "url": url})

# Build output
output = {
    "platform": "xiaohongshu",
    "original_url": f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else INPUT_URL,
    "author_name": author,
    "content": content,
    "media": media,
}
if avatar:
    output["author_avatar_url"] = avatar
if posted_at:
    output["posted_at"] = posted_at

print(json.dumps(output, ensure_ascii=False))
