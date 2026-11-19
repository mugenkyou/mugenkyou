#!/usr/bin/env python3
"""
Local live preview of the profile README: python scripts/preview.py [port]
Open http://localhost:8000 . The page reloads itself whenever README.md or any
card SVG changes (e.g. after re-running render_readme_cards.py).

README.md here is plain HTML, so it is injected as-is (no markdown renderer needed).
"""
import glob
import http.server
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>README preview</title>
<style>
body{margin:0;background:#fff;font:16px -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;color:#1f2328}
.box{max-width:830px;margin:32px auto;border:1px solid #d1d9e0;border-radius:6px;padding:24px}
.box img{max-width:100%;vertical-align:top}
.tag{font:12px ui-monospace,monospace;color:#59636e;margin-bottom:12px}
@media (prefers-color-scheme:dark){body{background:#0d1117;color:#f0f6fc}.box{border-color:#3d444d}}
</style></head><body><div class="box"><div class="tag">mugenkyou / README.md (live preview)</div><div id="md"></div></div>
<script>
let v = null;
async function load(){
  const md = await (await fetch('/README.md?t=' + Date.now())).text();
  // cache-bust card images so re-rendered SVGs replay their animations
  document.getElementById('md').innerHTML = md.replace(/(\\.svg)(")/g, '$1?t=' + Date.now() + '$2');
}
async function poll(){
  try {
    const nv = await (await fetch('/__version')).text();
    if (v !== null && nv !== v) await load();
    v = nv;
  } catch (e) {}
  setTimeout(poll, 800);
}
load(); poll();
</script></body></html>"""


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_text(self, body, ctype):
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            return self.send_text(PAGE, "text/html; charset=utf-8")
        if path == "/__version":
            files = [os.path.join(ROOT, "README.md")] + glob.glob(os.path.join(ROOT, "cards", "*.svg"))
            return self.send_text(str(max(os.path.getmtime(f) for f in files if os.path.exists(f))), "text/plain")
        return super().do_GET()

    def log_message(self, *a):  # keep the terminal quiet
        pass


if __name__ == "__main__":
    print(f"README preview: http://localhost:{PORT}")
    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
