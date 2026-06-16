#!/usr/bin/env python3
"""Capture an X/Twitter post and output JSON for secret-collector.

Requires: proxy access to X/Twitter, yt-dlp for video posts.
"""

import html
import json
import os
import re
import subprocess
import sys
import urllib.request

if len(sys.argv) < 2:
    print("Usage: x_capture.py <TWEET_URL>", file=sys.stderr)
    sys.exit(1)

TWEET_URL = sys.argv[1]
PROXY = os.environ.get("HTTPS_PROXY", "http://192.168.39.240:7890")

def get_oembed(url):
    """Fetch oembed metadata for a tweet."""
    oembed_url = f"https://publish.twitter.com/oembed?url={url}"
    req = urllib.request.Request(oembed_url)
    req.set_proxy(PROXY, "https")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def extract_content(html_text):
    """Extract clean text content from oembed html field."""
    # Remove script tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_text, flags=re.DOTALL)
    # Remove all HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # HTML unescape
    text = html.unescape(text)
    # Remove lines starting with — or &mdash; (author/date line)
    lines = text.split('\n')
    lines = [l for l in lines if not l.strip().startswith('—') and not l.strip().startswith('–')]
    # Remove trailing pic.twitter.com links
    text = '\n'.join(lines).strip()
    text = re.sub(r'\s*pic\.twitter\.com/\S+\s*$', '', text)
    return text.strip()

def extract_images(url):
    """Extract image URLs from tweet page HTML."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    req.set_proxy(PROXY, "https")
    with urllib.request.urlopen(req) as resp:
        html_content = resp.read().decode()

    media_urls = re.findall(r'https://pbs\.twimg\.com/media/[\w\-]+\.(?:jpg|png|jpeg)', html_content)
    # Filter: exclude profile images and video thumbnails
    media_urls = [u for u in media_urls
                  if 'profile_images' not in u and 'amplify_video_thumb' not in u]
    return list(set(media_urls))

def is_video_post(url):
    """Check if tweet is a video post (has amplify_video_thumb but no media images)."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    req.set_proxy(PROXY, "https")
    with urllib.request.urlopen(req) as resp:
        html_content = resp.read().decode()

    has_video_thumb = 'amplify_video_thumb' in html_content
    media_imgs = re.findall(r'https://pbs\.twimg\.com/media/[\w\-]+\.(?:jpg|png|jpeg)', html_content)
    non_thumb = [u for u in media_imgs if 'amplify_video_thumb' not in u and 'profile_images' not in u]
    return has_video_thumb and not non_thumb

def download_video(url, output_path="/tmp/x_video.mp4"):
    """Download video using yt-dlp."""
    cmd = [
        "yt-dlp", "--no-warnings", "--no-cache-dir",
        "--proxy", PROXY,
        "--force-overwrites",
        "-f", "hls-600/hls-151/best",
        "-o", output_path,
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"yt-dlp warning: {result.stderr}", file=sys.stderr)
    return output_path

# 1. Get oembed metadata
oembed = get_oembed(TWEET_URL)
author_name = oembed.get("author_name", "")
content = extract_content(oembed.get("html", ""))

# 2. Build output
original_url = TWEET_URL
# Normalize to status URL format
status_match = re.search(r'(https?://(?:twitter\.com|x\.com)/\w+/status/\d+)', TWEET_URL)
if status_match:
    original_url = status_match.group(1)

output = {
    "platform": "x",
    "original_url": original_url,
    "author_name": author_name,
    "content": content,
    "media": [],
}

# 3. Extract media
if is_video_post(TWEET_URL):
    video_path = download_video(TWEET_URL)
    output["media"] = [{"kind": "video", "url": video_path}]
else:
    images = extract_images(TWEET_URL)
    for img_url in images:
        output["media"].append({"kind": "image", "url": img_url + ":large"})

print(json.dumps(output, ensure_ascii=False))
