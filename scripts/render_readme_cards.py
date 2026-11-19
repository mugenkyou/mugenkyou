#!/usr/bin/env python3
"""
Render the profile README's cards as animated SVGs into cards/.

Design: "Three Worlds", matched to avivashishta.com (paper, ink, and one colour per
world: BUILD blue, BRAND red, LEARN yellow; Instrument Serif, Geist, Geist Mono).

Every card is a standalone SVG shown through <img>, so it can only use what GitHub
allows there: inline CSS animations, SMIL and fonts embedded as data URIs (no JS,
no external requests). Fonts are subset WOFFs in fonts/ (SIL OFL).

Live numbers come from data/contributions.json (fetch_contributions.py). The
brand and blog numbers are set by hand below; they come from data/stats.json in
the avivashishta.com repo.

Run by .github/workflows/update-profile-art.yml after fetch_contributions.py.
"""
import base64
import datetime
import json
import os
import re
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "data", "contributions.json")
OUT = os.path.join(ROOT, "cards")
FONTS = os.path.join(ROOT, "fonts")

# ---- hand-set numbers (update from avivashishta.com data/stats.json) --------
REEL_VIEWS = "12.7M"
BLOG_READERS = "27.5K"

# ---- brand tokens -----------------------------------------------------------
PAPER = "#0b0c0f"
PAPER_DEEP = "#1c1d21"
INK = "#f5f5f7"
INK_SOFT = "#c7c7cc"
MUTED = "#8e8e93"
RULE = "#2a2b30"
TECH = "#e8173d"  # the one accent: race red
STUDIO = "#ef3b2d"
LEARN = "#ffc81a"
W = 880  # full card width, GitHub's README column at 100%

SERIF = "'Instrument Serif', Georgia, serif"
SANS = "Geist, system-ui, -apple-system, sans-serif"
MONO = "'Geist Mono', ui-monospace, SFMono-Regular, Menlo, monospace"

FONT_FILES = {
    "serif": ("Instrument Serif", "normal", 400, "serif-400.woff"),
    "serif-i": ("Instrument Serif", "italic", 400, "serif-italic.woff"),
    "sans": ("Geist", "normal", 400, "geist-400.woff"),
    "sans-b": ("Geist", "normal", 600, "geist-600.woff"),
    "mono": ("Geist Mono", "normal", 400, "geistmono-400.woff"),
}

BASE_CSS = """
@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@keyframes pop{0%{opacity:0;transform:scale(.3)}70%{opacity:1;transform:scale(1.15)}100%{opacity:1;transform:none}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
@keyframes nudge{0%,100%{transform:none}50%{transform:translateX(4px)}}
@keyframes nudgeup{0%,100%{transform:none}50%{transform:translate(3px,-3px)}}
.r{opacity:0;animation:rise .8s cubic-bezier(.2,.7,.2,1) both;transform-box:fill-box}
.f{opacity:0;animation:fade .9s ease-out both}
.g{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:grow .8s cubic-bezier(.2,.7,.2,1) both}
.p{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .4s ease-out both}
.live{animation:pulse 1.6s ease-in-out infinite}
.n{transform-box:fill-box;animation:nudge 1.8s ease-in-out infinite}
.nu{transform-box:fill-box;animation:nudgeup 1.8s ease-in-out infinite}
@keyframes tilein{0%{opacity:0;transform:translateY(90px) scale(.6) rotate(-9deg)}55%{opacity:1;transform:translateY(-10px) scale(1.05) rotate(2deg)}75%{transform:translateY(3px) scale(.98) rotate(-.8deg)}90%{transform:translateY(-1px) scale(1.01) rotate(.2deg)}100%{opacity:1;transform:none}}
@keyframes slidein{from{opacity:0;transform:translateX(-26px)}to{opacity:1;transform:none}}
@keyframes arrowin{0%{opacity:0;transform:translateX(-30px)}60%{opacity:1;transform:translateX(6px)}100%{opacity:1;transform:none}}
@keyframes roll{from{transform:translateY(60px)}to{transform:none}}
@keyframes sheen{0%{transform:translateX(-260px) skewX(-20deg)}22%,100%{transform:translateX(420px) skewX(-20deg)}}
@keyframes ring{0%{opacity:.7;transform:scale(.2)}100%{opacity:0;transform:scale(2.4)}}
.ti{opacity:0;transform-box:fill-box;transform-origin:50% 60%;animation:tilein 1.1s cubic-bezier(.2,.8,.2,1) both}
.sl{opacity:0;transform-box:fill-box;animation:slidein .6s cubic-bezier(.2,.7,.2,1) both}
.ai{opacity:0;transform-box:fill-box;animation:arrowin .7s cubic-bezier(.2,.7,.2,1) both}
.ro{transform-box:fill-box;animation:roll .8s cubic-bezier(.15,.8,.2,1) both}
.sh{animation:sheen 5s ease-in-out infinite}
.rg{opacity:0;transform-box:fill-box;transform-origin:center;animation:ring 1s ease-out both}
@media (prefers-reduced-motion: reduce){.r,.f,.g,.p,.live,.n,.nu,.ti,.sl,.ai,.ro,.rg{animation:none!important;opacity:1!important;transform:none!important}.sh,.rg{display:none}}
"""


def font_face(keys):
    out = []
    for k in keys:
        fam, style, weight, fn = FONT_FILES[k]
        b64 = base64.b64encode(open(os.path.join(FONTS, fn), "rb").read()).decode()
        out.append(
            f"@font-face{{font-family:'{fam}';font-style:{style};font-weight:{weight};"
            f"src:url(data:font/woff;base64,{b64}) format('woff')}}"
        )
    return "".join(out)


GAP = 12          # gap between cards, baked into the SVGs (GitHub's own spacing is uneven)
BOTTOM = 12       # bottom padding per row, matching GAP
COL = W / 3       # each card in a row of three is exactly a third of the column


def svg(w, h, body, fonts, label, extra_css="", left=0, right=0, bottom=BOTTOM):
    """Card of w x h drawn at x=left inside a transparent canvas, padded so rows tile exactly."""
    if left:
        body = f'<g transform="translate({left:.3f} 0)">{body}</g>'
    w, h = w + left + right, h + bottom
    css = font_face(fonts) + BASE_CSS + extra_css
    if os.environ.get("STATIC"):  # preview: show every animation at its end state
        css += ".r,.f,.g,.gx,.p,.live,.n,.nu,.ti,.sl,.ai,.ro,.car{animation:none!important;opacity:1!important;transform:none!important}.sh,.rg,.st,.sw{display:none}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.3f}" height="{h}" viewBox="0 0 {w:.3f} {h}" '
        f'role="img" aria-label="{escape(label)}"><title>{escape(label)}</title>'
        f"<style>{css}</style>{body}</svg>"
    )


def write(name, content):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"wrote cards/{name} ({len(content) // 1024} KB)")


def d(s):  # animation delay attribute
    return f'style="animation-delay:{s:.2f}s"'


def wrap(text, n):
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > n:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + [line] if line else lines


def text_lines(x, y, lines, lh, attrs):
    return "".join(
        f'<text x="{x}" y="{y + i * lh}" {attrs}>{escape(l)}</text>' for i, l in enumerate(lines)
    )


# ---- 1 · hero -----------------------------------------------------------------
HERO_IMG = os.path.join(ROOT, "image.png")
NIGHT, RACE_RED = PAPER, TECH
HERO_CSS = """
@keyframes carin{0%{opacity:0;transform:translateX(120px) scale(1.06)}100%{opacity:1;transform:none}}
@keyframes streak{0%{transform:translateX(0);opacity:0}10%{opacity:1}100%{transform:translateX(-1100px);opacity:0}}
@keyframes glow{0%,100%{opacity:.35}50%{opacity:.8}}
@keyframes sweep{0%{transform:translateX(-500px) skewX(-18deg)}35%,100%{transform:translateX(1000px) skewX(-18deg)}}
.car{opacity:0;transform-box:view-box;animation:carin 1.6s cubic-bezier(.16,.84,.24,1) .2s both}
.st{animation:streak 1.4s linear infinite}
.gl{animation:glow 2.4s ease-in-out infinite}
.sw{animation:sweep 6s ease-in-out 2s infinite}
@media (prefers-reduced-motion: reduce){.car{animation:none!important;opacity:1!important;transform:none!important}.st,.sw{display:none}.gl{animation:none!important}}
"""


def car_photo(width=1100):
    """The car shot as an embedded JPEG data URI (no external requests inside <img>)."""
    import io
    from PIL import Image
    im = Image.open(HERO_IMG).convert("RGB")
    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82, optimize=True, progressive=True)
    return im.size, base64.b64encode(buf.getvalue()).decode()


def hero():
    h = 476
    (pw, ph), b64 = car_photo()
    iw = 780                                   # car drawn on the right, front wing fading under the text
    ih = iw * ph / pw
    ix, iy = W - iw + 40, h - ih
    streaks = "".join(
        f'<rect class="st" style="animation-delay:{1.8 + k * 0.37:.2f}s;animation-duration:{1.1 + (k % 3) * 0.25:.2f}s" '
        f'x="{W + 20}" y="{y}" width="{w}" height="{1.5 if k % 2 else 1}" rx="1" fill="{c}" opacity="0"/>'
        for k, (y, w, c) in enumerate([(392, 140, "#ffffff"), (418, 90, RACE_RED), (440, 180, "#ffffff"),
                                        (366, 60, "#ffffff"), (456, 120, RACE_RED), (404, 70, "#ffffff")])
    )
    body = f"""
<defs>
  <clipPath id="card"><rect width="{W}" height="{h}" rx="14"/></clipPath>
  <linearGradient id="fadex" gradientUnits="userSpaceOnUse" x1="{ix}" y1="0" x2="{ix + 330}" y2="0">
    <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity="1"/></linearGradient>
  <linearGradient id="fadey" gradientUnits="userSpaceOnUse" x1="0" y1="{iy}" x2="0" y2="{iy + 90}">
    <stop offset="0" stop-color="#000"/><stop offset="1" stop-color="#000" stop-opacity="0"/></linearGradient>
  <mask id="fade"><rect width="{W}" height="{h}" fill="url(#fadex)"/><rect x="0" y="{iy}" width="{W}" height="90" fill="url(#fadey)"/></mask>
  <linearGradient id="beam" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>
    <stop offset=".5" stop-color="#fff" stop-opacity=".16"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
  <linearGradient id="scrim" x1="0" x2="1"><stop offset="0" stop-color="{NIGHT}" stop-opacity=".92"/>
    <stop offset=".55" stop-color="{NIGHT}" stop-opacity=".6"/><stop offset="1" stop-color="{NIGHT}" stop-opacity="0"/></linearGradient>
  <radialGradient id="redglow"><stop offset="0" stop-color="{RACE_RED}" stop-opacity=".55"/><stop offset="1" stop-color="{RACE_RED}" stop-opacity="0"/></radialGradient>
  <linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="600" y2="0">
    <stop offset="0" stop-color="#ffffff"/><stop offset=".42" stop-color="#ffffff"/>
    <stop offset=".5" stop-color="{RACE_RED}"/><stop offset=".58" stop-color="#ffffff"/>
    <stop offset="1" stop-color="#ffffff"/>
    <animateTransform attributeName="gradientTransform" type="translate" values="-600 0;600 0;600 0"
      keyTimes="0;.45;1" dur="7s" begin="1.6s" repeatCount="indefinite"/>
  </linearGradient>
</defs>
<g clip-path="url(#card)">
  <rect width="{W}" height="{h}" fill="{NIGHT}"/>
  <ellipse class="gl" cx="{W - 220}" cy="{h - 30}" rx="300" ry="60" fill="url(#redglow)"/>
  <g class="car"><g mask="url(#fade)">
    <image href="data:image/jpeg;base64,{b64}" x="{ix:.1f}" y="{iy:.1f}" width="{iw}" height="{ih:.1f}"/>
    <rect class="sw" x="0" y="{iy:.1f}" width="140" height="{ih:.1f}" fill="url(#beam)" transform="translate(-500 0)"/>
  </g></g>
  <rect x="0" y="0" width="520" height="{h}" fill="url(#scrim)"/>
  {streaks}
</g>
<g class="f" {d(0)}>
  <rect class="live" x="48" y="49" width="8" height="8" rx="2" fill="{RACE_RED}"/>
  <text x="66" y="57" font-family="{MONO}" font-size="12" letter-spacing="1" fill="#8e8e93">SOFTWARE ENGINEER</text>
</g>
<text class="r" {d(0.15)} x="44" y="190" font-family="{SERIF}" font-size="116" letter-spacing="-2.5" fill="#ffffff">Sachin</text>
<text class="r" {d(0.3)} x="44" y="290" font-family="{SERIF}" font-style="italic" font-size="116" letter-spacing="-2.5" fill="url(#shine)">Patel</text>
<g class="r" {d(0.55)}>
  {text_lines(48, 338, ["Building software, breaking it, fixing it,", "and occasionally making something useful.", "Interested in AI, systems, and the", "engineering behind products people use."], 27, f'font-family="{SANS}" font-size="18" fill="#c7c7cc"')}
</g>
<g class="f" {d(0.8)}>
  <text x="48" y="452" font-family="{MONO}" font-size="13" fill="#ffffff">github.com/mugenkyou</text>
  <text class="nu" x="216" y="452" font-family="{MONO}" font-size="13" fill="{RACE_RED}">&#8599;</text>
</g>
"""
    write("hero.svg", svg(W, h, body, ["serif", "serif-i", "sans", "mono"],
                          "Sachin Patel. Building software, breaking it, fixing it, and occasionally making something useful. Interested in AI, systems, and the engineering behind products people use.",
                          extra_css=HERO_CSS))


# ---- 2 · world tiles ----------------------------------------------------------
TILE_W, TILE_H = 880 / 3 - 8, 210  # 285.33: two 12px gaps across the row


def count_up(num, word, x, y, attrs, begin, dur=1.1, frames=18):
    """Number counts up from 0 with SMIL <set> frames (works inside <img>), easing out."""
    m = re.match(r"([\d.,]+)(.*)", num)
    val, suf = float(m.group(1).replace(",", "")), m.group(2)
    dec = len(m.group(1).split(".")[1]) if "." in m.group(1) else 0
    sep = "," if "," in m.group(1) else ""
    tail = f' <tspan font-style="italic">{escape(word)}</tspan>'
    if os.environ.get("STATIC"):
        return f'<text x="{x}" y="{y}" {attrs}>{escape(num)}{tail}</text>'
    out = []
    for i in range(frames + 1):
        e = 1 - (1 - i / frames) ** 3
        txt = num if i == frames else f"{val * e:{sep}.{dec}f}{suf}"
        on = begin + dur * i / frames
        off = "" if i == frames else f'<set attributeName="opacity" to="0" begin="{begin + dur * (i + 1) / frames:.3f}s"/>'
        out.append(f'<text x="{x}" y="{y}" {attrs} opacity="0">{escape(txt)}{tail}'
                   f'<set attributeName="opacity" to="1" begin="{on:.3f}s"/>{off}</text>')
    return "".join(out)


def tile(name, label, color, on, num, word, blurb, delay, pos):
    lines = wrap(blurb, 34)
    blurb_svg = "".join(
        f'<text class="r" {d(delay + 0.75 + i * 0.1)} x="24" y="{150 + i * 20}" font-family="{SANS}" '
        f'font-size="14" fill="{on}" opacity=".92">{escape(l)}</text>'
        for i, l in enumerate(lines)
    )
    body = f"""
<defs>
  <clipPath id="card"><rect width="{TILE_W}" height="{TILE_H}" rx="14"/></clipPath>
  <clipPath id="slot"><rect x="0" y="62" width="{TILE_W}" height="62"/></clipPath>
  <linearGradient id="gl" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>
    <stop offset=".5" stop-color="#fff" stop-opacity=".35"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
</defs>
<g class="ti" {d(delay)}>
  <g clip-path="url(#card)">
    <rect width="{TILE_W}" height="{TILE_H}" fill="{color}"/>
    <circle class="rg" {d(delay + 0.5)} cx="{TILE_W - 40}" cy="{TILE_H - 40}" r="60" fill="none" stroke="{on}" stroke-opacity=".5" stroke-width="2"/>
    <rect class="sh" style="animation-delay:{delay + 1.4:.2f}s" x="0" y="-20" width="90" height="{TILE_H + 40}" fill="url(#gl)" transform="translate(-260 0)"/>
  </g>
  <text class="sl" {d(delay + 0.35)} x="24" y="38" font-family="{MONO}" font-size="12" letter-spacing="1.2" fill="{on}">{label}</text>
  <g class="ai" {d(delay + 0.5)}><text class="n" style="animation-delay:{delay + 1.3:.2f}s" x="250" y="38" font-family="{MONO}" font-size="14" fill="{on}">&#8594;</text></g>
  <g clip-path="url(#slot)"><g class="ro" {d(delay + 0.45)}>
    {count_up(num, word, 22, 112, f'font-family="{SERIF}" font-size="44" fill="{on}"', delay + 0.45)}
  </g></g>
  {blurb_svg}
</g>
"""
    write(f"{name}.svg", svg(TILE_W, TILE_H, body, ["serif", "serif-i", "sans", "mono"],
                             f"{label}: {num} {word}. {blurb}", left=4 * pos, right=8 - 4 * pos))


# ---- 3 · activity (monthly bars) ------------------------------------------------
def activity(data):
    h = 340
    monthly = data["monthly"][-12:]
    best = max(monthly[:-1] or monthly, key=lambda m: m["total"])
    top = best["total"]
    x0, x1, base, maxh, gap = 40, 600, 292, 140, 10
    bw = (x1 - x0 - gap * (len(monthly) - 1)) / len(monthly)
    bars = []
    for i, m in enumerate(monthly):
        partial = i == len(monthly) - 1
        is_best = m is best
        bh = max(4, round(m["total"] / top * maxh))
        x = x0 + i * (bw + gap)
        fill = TECH if is_best else ("#3a3b40" if partial else INK)
        label = datetime.date.fromisoformat(m["month"] + "-01").strftime("%b")
        bars.append(
            f'<rect class="g" style="animation-delay:{2.2 + i * 0.07:.2f}s" x="{x:.1f}" y="{base - bh}" '
            f'width="{bw:.1f}" height="{bh}" rx="4" fill="{fill}"><title>{label}: {m["total"]:,}</title></rect>'
            f'<text class="f" style="animation-delay:{2.2 + i * 0.07:.2f}s" x="{x + bw / 2:.1f}" y="{base + 22}" '
            f'text-anchor="middle" font-family="{MONO}" font-size="11" fill="{MUTED}">{label}</text>'
        )
        if is_best:
            bars.append(
                f'<text class="p" style="animation-delay:3.2s" x="{x + bw / 2:.1f}" y="{base - bh - 10}" '
                f'text-anchor="middle" font-family="{MONO}" font-size="11" fill="{TECH}">{m["total"]:,}</text>'
            )
    cs = data["current_streak"]["length"]
    ls = data["longest_streak"]["length"]
    streak_note = "current streak, and the longest" if cs >= ls else f"current streak, longest {ls}"
    total_days = len(data["days"])
    stats = [
        (f'{cs} <tspan font-style="italic">days</tspan>', streak_note),
        (f'{data["active_days"]}<tspan fill="#5a5b60"> / {total_days}</tspan>', "days with a commit"),
        (f'{data["best_day"]["count"]}', "on the busiest day"),
    ]
    side = []
    for i, (big, small) in enumerate(stats):
        y = 104 + i * 92
        side.append(
            f'<g class="r" {d(2.6 + i * 0.15)}>'
            f'<text x="650" y="{y}" font-family="{SERIF}" font-size="40" fill="{INK}">{big}</text>'
            f'<text x="650" y="{y + 24}" font-family="{SANS}" font-size="13" fill="{MUTED}">{small}</text></g>'
        )
        if i < 2:
            side.append(f'<rect class="f" {d(2.6)} x="650" y="{y + 44}" width="190" height="1" fill="{RULE}"/>')
    body = f"""
<rect width="{W}" height="{h}" rx="14" fill="{PAPER}"/>
<text class="f" {d(1.9)} x="40" y="58" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{MUTED}">THE LAST 12 MONTHS ON GITHUB</text>
<text class="r" {d(2.0)} x="38" y="114" font-family="{SERIF}" font-size="52" fill="{INK}">{data["total_contributions"]:,} <tspan font-style="italic">contributions</tspan></text>
{''.join(bars)}
{''.join(side)}
"""
    write("activity.svg", svg(W, h, body, ["serif", "serif-i", "sans", "mono"],
                              f'{data["total_contributions"]:,} contributions in the last year, {cs}-day streak'))


# ---- 4 · repo cards -----------------------------------------------------------
REPO_W, REPO_H = 880 / 3 - 8, 210
REPOS = [
    ("mimir-nest", "An open-source student platform for system design practice, placement preparation, learning resources, and productivity tools.", "Students · Open source · Product", TECH, "FLAGSHIP"),
    ("titan-env", "Autonomous satellite fault recovery under radiation stress, with GRPO-trained Qwen3 support and a live 3D dashboard.", "Research · Reinforcement learning · Simulation", INK, ""),
    ("mirailens", "Connects AI clients to real Chrome sessions with browser controls, human takeover, permissions, and safety checks.", "Developer tools · MCP · Browser automation", LEARN, ""),
]


def repo_card(i, name, desc, tags, color, badge, stars):
    delay = 4.6 + i * 0.12
    meta = f"github  ·  ★ {stars}" if stars else "github"
    tag_lines = wrap(tags, 36)
    desc_y = 62 + len(tag_lines) * 16 + 14
    badge_svg = (f'<text x="{REPO_W - 24:.1f}" y="38" text-anchor="end" font-family="{MONO}" font-size="11" '
                 f'letter-spacing="1" fill="{color}">{badge}</text>') if badge else ""
    body = f"""
<rect width="{REPO_W}" height="{REPO_H}" rx="14" fill="{PAPER}"/>
<g class="r" {d(delay)}>
  <rect x="24" y="30" width="8" height="8" rx="2" fill="{color}"/>
  <text x="40" y="39" font-family="{SANS}" font-weight="600" font-size="18" fill="{INK}">{escape(name)}</text>
  {badge_svg}
  {text_lines(24, 62, tag_lines, 16, f'font-family="{MONO}" font-size="11" fill="{MUTED}"')}
  {text_lines(24, desc_y, wrap(desc, 34), 21, f'font-family="{SANS}" font-size="14" fill="{INK_SOFT}"')}
  <text x="24" y="{REPO_H - 24}" font-family="{MONO}" font-size="12" fill="{MUTED}">{escape(meta)}</text>
</g>
"""
    write(f"repo-{name}.svg", svg(REPO_W, REPO_H, body, ["sans", "sans-b", "mono"], f"{name}: {desc}",
                                  left=4 * i, right=8 - 4 * i))


def section_title(text, italic, theme):
    fg = "#e6edf3" if theme == "dark" else "#111111"
    body = (
        f'<text class="r" {d(4.4)} x="2" y="46" font-family="{SERIF}" font-size="34" fill="{fg}">{escape(text)} '
        f'<tspan font-style="italic">{escape(italic)}</tspan></text>'
    )
    write(f"title-coding-{theme}.svg", svg(W, 64, body, ["serif", "serif-i"], f"{text} {italic}", bottom=0))


# ---- 5 · blue contribution graph -----------------------------------------------
HEAT = [PAPER_DEEP, "#3a0b16", "#6e1024", "#b0132f", TECH, "#ff6b81"]  # dark -> hot red


def level_for(c):
    return 0 if c == 0 else 1 if c <= 5 else 2 if c <= 15 else 3 if c <= 30 else 4 if c <= 50 else 5


def heatmap(data):
    days = data["days"]
    first = datetime.date.fromisoformat(days[0]["date"])
    lead = (first.weekday() + 1) % 7  # sunday = 0
    cell, step, gx, gy = 12, 15, 44, 96
    cells, months, seen = [], [], set()
    for i, day in enumerate(days):
        k = i + lead
        col, row = divmod(k, 7)
        date = datetime.date.fromisoformat(day["date"])
        if date.day <= 7 and (date.year, date.month) not in seen and row == 0:
            seen.add((date.year, date.month))
            months.append((col, date.strftime("%b")))
        c = day["count"]
        delay = 1.0 + col * 0.03 + row * 0.02
        cells.append(
            f'<rect class="p" style="animation-delay:{delay:.2f}s" x="{gx + col * step}" y="{gy + row * step}" '
            f'width="{cell}" height="{cell}" rx="3" fill="{HEAT[level_for(c)]}">'
            f'<title>{day["date"]}: {c} contribution{"s" if c != 1 else ""}</title></rect>'
        )
    ncols = (len(days) + lead + 6) // 7
    right = gx + ncols * step - 3
    labels = "".join(
        f'<text x="{gx + col * step}" y="{gy + 7 * step + 16}" font-family="{MONO}" font-size="11" fill="{MUTED}">{m}</text>'
        for col, m in months if col < ncols - 12
    )
    legend_x = right - len(HEAT) * 14
    legend = "".join(
        f'<rect x="{legend_x + i * 14}" y="{gy + 7 * step + 6}" width="11" height="11" rx="2.5" fill="{c}"/>'
        for i, c in enumerate(HEAT)
    )
    h = gy + 7 * step + 44
    body = f"""
<rect width="{W}" height="{h}" rx="14" fill="{PAPER}"/>
<text class="r" {d(0.8)} x="42" y="62" font-family="{SERIF}" font-size="34" fill="{INK}">Every day, <tspan font-style="italic" fill="{TECH}">in red</tspan></text>
<text class="f" {d(0.8)} x="{right}" y="60" text-anchor="end" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{MUTED}">REFRESHED DAILY</text>
{''.join(cells)}
<g class="f" {d(2.4)}>{labels}
<text x="{legend_x - 8}" y="{gy + 7 * step + 16}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MUTED}">less</text>
{legend}
<text x="{legend_x + len(HEAT) * 14 + 2}" y="{gy + 7 * step + 16}" font-family="{MONO}" font-size="11" fill="{MUTED}">more</text></g>
"""
    write("heatmap.svg", svg(W, h, body, ["serif", "serif-i", "mono"],
                             f'Contribution graph: {data["total_contributions"]:,} contributions in the last year'))


# ---- 6 · most used languages ----------------------------------------------------
# shortcut: hand-set from the GitHub language stats card, update by hand (or fetch per-repo /languages) when they drift
LANGS = [("Python", 80.80), ("TypeScript", 8.88), ("JavaScript", 3.14),
         ("HTML", 2.94), ("CSS", 2.28), ("Jupyter Notebook", 1.95)]
LANG_COLORS = [TECH, INK, LEARN, "#8e8e93", "#5a5b60", "#3a3b40"]
GROWX = "@keyframes growx{from{transform:scaleX(0)}to{transform:scaleX(1)}}" \
        ".gx{transform-box:fill-box;transform-origin:left;transform:scaleX(0);animation:growx 1.2s cubic-bezier(.2,.7,.2,1) both}" \
        "@media (prefers-reduced-motion: reduce){.gx{animation:none!important;transform:none!important}}"


# last row: languages card (50%) + two contact tiles (25% each), 12px gaps baked in
ROW_H = 210
LANG_W = W / 2 - 8          # image 440 wide: card 0..432, 8px right pad
BTN_W = W / 4 - 8           # 212: linkedin at 444..656, email at 668..880


def languages():
    total = sum(p for _, p in LANGS)
    x0, bw, by = 24, LANG_W - 48, 98
    segs, x = [], x0
    for (name, p), c in zip(LANGS, LANG_COLORS):
        w = p / total * bw
        segs.append(f'<rect x="{x:.2f}" y="{by}" width="{w:.2f}" height="10" fill="{c}"><title>{name}: {p:.2f}%</title></rect>')
        x += w
    legend = []
    for i, ((name, p), c) in enumerate(zip(LANGS, LANG_COLORS)):
        cx, cy = x0 + (i % 2) * 200, 140 + (i // 2) * 24
        legend.append(
            f'<g class="r" {d(5.2 + i * 0.06)}>'
            f'<rect x="{cx}" y="{cy - 9}" width="9" height="9" rx="2" fill="{c}"/>'
            f'<text x="{cx + 17}" y="{cy}" font-family="{SANS}" font-size="13" fill="{INK}">{escape(name)}</text>'
            f'<text x="{cx + 184}" y="{cy}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MUTED}">{p:.1f}%</text></g>'
        )
    top_name, top_p = LANGS[0]
    body = f"""
<defs><clipPath id="bar"><rect x="{x0}" y="{by}" width="{bw:.2f}" height="10" rx="5"/></clipPath></defs>
<rect width="{LANG_W}" height="{ROW_H}" rx="14" fill="{PAPER}"/>
<text class="f" {d(4.9)} x="24" y="38" font-family="{MONO}" font-size="12" letter-spacing="1.2" fill="{MUTED}">MOST USED LANGUAGES</text>
<text class="r" {d(5.0)} x="22" y="80" font-family="{SERIF}" font-size="38" fill="{INK}">{top_p:.1f}% <tspan font-style="italic" fill="{TECH}">{escape(top_name)}</tspan></text>
<rect x="{x0}" y="{by}" width="{bw:.2f}" height="10" rx="5" fill="{PAPER_DEEP}"/>
<g clip-path="url(#bar)"><g class="gx" {d(5.2)}>{''.join(segs)}</g></g>
{''.join(legend)}
"""
    write("languages.svg", svg(LANG_W, ROW_H, body, ["serif", "serif-i", "sans", "mono"],
                               "Most used languages: " + ", ".join(f"{n} {p:.2f}%" for n, p in LANGS),
                               extra_css=GROWX, right=8))


# ---- 7 · contact tiles --------------------------------------------------------------
LINKEDIN_PATH = ("M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046"
                 "c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 "
                 "2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 "
                 ".774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z")


def button(name, label, lines, icon, bg, fg, sub, left, right, delay):
    last = ROW_H - 26
    first = last - 21 * (len(lines) - 1)
    value = text_lines(24, first, lines, 21, f'font-family="{SANS}" font-weight="600" font-size="17" fill="{fg}"')
    body = f"""
<defs>
  <clipPath id="btn"><rect width="{BTN_W}" height="{ROW_H}" rx="14"/></clipPath>
  <linearGradient id="gl" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>
    <stop offset=".5" stop-color="#fff" stop-opacity=".3"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
</defs>
<g class="ti" {d(delay)}>
  <g clip-path="url(#btn)">
    <rect width="{BTN_W}" height="{ROW_H}" fill="{bg}"/>
    <rect class="sh" style="animation-delay:{delay + 1.2:.2f}s" x="0" y="-20" width="90" height="{ROW_H + 40}" fill="url(#gl)" transform="translate(-260 0)"/>
  </g>
  <g class="p" {d(delay + 0.4)}><g transform="translate(24 24) scale(1.75)" fill="{fg}">{icon}</g></g>
  <text class="nu" style="animation-delay:{delay + 1:.2f}s" x="{BTN_W - 40:.1f}" y="44" font-family="{MONO}" font-size="20" fill="{fg}">&#8599;</text>
  <text class="sl" {d(delay + 0.5)} x="24" y="{first - 30}" font-family="{MONO}" font-size="11" letter-spacing="1.2" fill="{sub}">{label}</text>
  <g class="r" {d(delay + 0.6)}>{value}</g>
</g>
"""
    write(f"btn-{name}.svg", svg(BTN_W, ROW_H, body, ["sans-b", "mono"], f"{label}: {''.join(lines)}",
                                 left=left, right=right))


def buttons():
    mail_icon = (f'<rect x="1" y="4" width="22" height="16" rx="2.5" fill="none" stroke="{INK}" stroke-width="2"/>'
                 f'<path d="M2 6l10 7 10-7" fill="none" stroke="{INK}" stroke-width="2" stroke-linejoin="round"/>')
    button("linkedin", "LINKEDIN", ["in/sachinskyte"], f'<path d="{LINKEDIN_PATH}"/>',
           "#0a66c2", "#ffffff", "#cfe0f5", left=4, right=4, delay=5.1)
    button("email", "EMAIL", ["sachinskyte", "@gmail.com"], mail_icon,
           PAPER_DEEP, INK, MUTED, left=8, right=0, delay=5.25)


def repo_stars():
    stars = {}
    try:
        import requests

        for name, *_ in REPOS:
            r = requests.get(f"https://api.github.com/repos/mugenkyou/{name}", timeout=10)
            if r.ok:
                stars[name] = r.json().get("stargazers_count", 0)
    except Exception as e:  # offline: keep going without stars
        print(f"stars unavailable: {e}")
    return stars


if __name__ == "__main__":
    data = json.load(open(DATA))
    hero()
    tile("build", "BUILT", INK, "#111111", "10+", "projects",
         "Projects shipped across AI, software and developer tools.", 3.1, 0)
    tile("brand", "IMPACT", STUDIO, "#ffffff", "3,000+", "users",
         "Mimir Nest users. Founded an open-source student platform.", 3.35, 1)
    tile("learn", "ACHIEVED", LEARN, "#111111", "3×", "podiums",
         "Hackathon podiums.", 3.6, 2)
    activity(data)
    stars = repo_stars()
    for i, (name, desc, tags, color, badge) in enumerate(REPOS):
        repo_card(i, name, desc, tags, color, badge, stars.get(name))
    section_title("What I'm", "coding", "dark")
    section_title("What I'm", "coding", "light")
    heatmap(data)
    languages()
    buttons()
