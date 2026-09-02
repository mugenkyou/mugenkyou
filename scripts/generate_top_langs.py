#!/usr/bin/env python3
"""
Generate a top-languages SVG card for GitHub profile (username: mugenkyou).
Fetches real repository language statistics from the GitHub API and outputs
data/top_languages.json and top-langs.svg.

Supports GITHUB_TOKEN environment variable.
"""

import json
import math
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

USERNAME = os.environ.get("GH_PROFILE_USER", "mugenkyou")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
CACHE_PATH = os.path.join(REPO_ROOT, "data", "top_languages.json")
SVG_PATH = os.path.join(REPO_ROOT, "top-langs.svg")

LANGUAGE_COLORS = {
    "Python": "#3572A5",
    "TypeScript": "#8A2BE2",
    "JavaScript": "#f1e05a",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "C": "#555555",
    "C++": "#f34b7d",
    "Java": "#b07219",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Shell": "#89e051",
    "PowerShell": "#012456",
    "PHP": "#4F5D95",
    "Ruby": "#701516",
    "Swift": "#F05138",
    "Kotlin": "#A97BFF",
    "Dart": "#00B4AB",
}

DEFAULT_COLORS = ["#00E5FF", "#8A2BE2", "#FF6B6B", "#27C93F", "#FFBD2E", "#E4405F"]


def make_request(url):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "mugenkyou-top-langs-bot/1.0")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_language_stats(user):
    page = 1
    repos = []
    while True:
        url = f"https://api.github.com/users/{user}/repos?per_page=100&page={page}&type=owner"
        data = make_request(url)
        if not data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1

    lang_totals = {}
    for repo in repos:
        # sensibly filter: skip forks, archived repos if appropriate
        if repo.get("fork"):
            continue
        langs_url = repo.get("languages_url")
        if not langs_url:
            continue
        try:
            langs = make_request(langs_url)
            for lang, count in langs.items():
                lang_totals[lang] = lang_totals.get(lang, 0) + int(count)
        except Exception as e:
            print(f"Warning: Failed to fetch languages for {repo.get('name')}: {e}", file=sys.stderr)

    return lang_totals


def load_cached_data():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if cached.get("username") == USERNAME and "languages" in cached:
                    print("Using cached language data from data/top_languages.json", file=sys.stderr)
                    return cached
        except Exception as e:
            print(f"Warning: Failed to read cache: {e}", file=sys.stderr)
    return None


def generate_svg(data):
    languages = data.get("languages", [])[:6]
    total_bytes = sum(item["bytes"] for item in languages) if languages else 1

    width = 420
    height = 185

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none">',
        '  <style>',
        '    .card-title { font: 600 14px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; fill: #00E5FF; }',
        '    .lang-name { font: 600 12px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; fill: #c9d1d9; }',
        '    .lang-pct { font: 400 12px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; fill: #8b949e; }',
        '  </style>',
        f'  <rect width="{width}" height="{height}" rx="8" fill="#0d1117" stroke="#30363d" stroke-width="1"/>',
        '  <text x="25" y="32" class="card-title">Most Used Languages</text>',
        '  <g transform="translate(25, 48)">',
        '    <rect width="370" height="8" rx="4" fill="#161b22"/>',
        '    <clipPath id="bar-clip">',
        '      <rect width="370" height="8" rx="4"/>',
        '    </clipPath>',
        '    <g clip-path="url(#bar-clip)">',
    ]

    # Render stacked bar segments
    current_x = 0.0
    bar_width = 370.0
    for idx, item in enumerate(languages):
        pct = item["percentage"]
        seg_w = (pct / 100.0) * bar_width
        color = item.get("color") or LANGUAGE_COLORS.get(item["name"]) or DEFAULT_COLORS[idx % len(DEFAULT_COLORS)]
        svg_parts.append(f'      <rect x="{current_x:.2f}" y="0" width="{seg_w:.2f}" height="8" fill="{color}"/>')
        current_x += seg_w

    svg_parts.extend([
        '    </g>',
        '  </g>',
    ])

    # Render language grid items (2 columns x 3 rows)
    for idx, item in enumerate(languages):
        col = idx % 2
        row = idx // 2
        x = 25 + col * 190
        y = 82 + row * 28
        color = item.get("color") or LANGUAGE_COLORS.get(item["name"]) or DEFAULT_COLORS[idx % len(DEFAULT_COLORS)]
        pct_str = f'{item["percentage"]:.2f}%'

        svg_parts.extend([
            f'  <g transform="translate({x}, {y})">',
            f'    <circle cx="5" cy="6" r="5" fill="{color}"/>',
            f'    <text x="16" y="10" class="lang-name">{item["name"]}</text>',
            f'    <text x="150" y="10" class="lang-pct" text-anchor="end">{pct_str}</text>',
            '  </g>',
        ])

    svg_parts.append('</svg>')
    return '\n'.join(svg_parts)


def main():
    print(f"Fetching GitHub language statistics for user: {USERNAME}...")
    try:
        lang_totals = fetch_language_stats(USERNAME)
        if not lang_totals:
            raise ValueError("No language statistics found from API.")

        sorted_langs = sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)
        top_6 = sorted_langs[:6]
        top_total_bytes = sum(b for _, b in top_6)

        languages_data = []
        for idx, (lang, bytes_cnt) in enumerate(top_6):
            pct = round((bytes_cnt / top_total_bytes) * 100, 2)
            color = LANGUAGE_COLORS.get(lang, DEFAULT_COLORS[idx % len(DEFAULT_COLORS)])
            languages_data.append({
                "name": lang,
                "bytes": bytes_cnt,
                "percentage": pct,
                "color": color
            })

        cache_data = {
            "username": USERNAME,
            "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_bytes": top_total_bytes,
            "languages": languages_data
        }

        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
        print(f"Updated data cache: {CACHE_PATH}")

    except Exception as e:
        print(f"API Fetch failed ({e}). Checking local cache...", file=sys.stderr)
        cache_data = load_cached_data()
        if not cache_data:
            print("Error: Could not fetch language statistics and no valid local cache exists.", file=sys.stderr)
            sys.exit(1)

    svg_content = generate_svg(cache_data)
    with open(SVG_PATH, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Generated top-languages SVG: {SVG_PATH}")


if __name__ == "__main__":
    main()
