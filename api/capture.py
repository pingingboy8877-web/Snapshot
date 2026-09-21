import io
import os
import re
import requests
from urllib.parse import urlparse
from http.server import BaseHTTPRequestHandler
from PIL import Image
from pptx import Presentation
from pptx.util import Inches

BROWSERLESS = "https://production-sfo.browserless.io"
MAX_TIMEOUT = 180

def bad(handler, message, status=400):
    body = ('{"error":' + __import__("json").dumps(message) + '}').encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)

def browserless(url, fmt, width, delay, paper, token):
    common = {
        "url": url,
        "viewport": {"width": width, "height": 900},
        "gotoOptions": {"waitUntil": "networkidle2", "timeout": 60000},
        "waitForTimeout": delay * 1000,
        "scrollPage": True,
    }
    if fmt == "pdf":
        endpoint = "/pdf"
        payload = {
            "url": url,
            "options": {
                "format": paper,
                "printBackground": True,
                "preferCSSPageSize": False,
                "margin": {"top": "0", "right": "0", "bottom": "0", "left": "0"},
            },
        }
    else:
        endpoint = "/screenshot"
        payload = {**common, "options": {"fullPage": True, "type": fmt, "quality": 92 if fmt == "jpeg" else 100}}
    r = requests.post(BROWSERLESS + endpoint, params={"token": token}, json=payload, timeout=MAX_TIMEOUT)
    if not r.ok:
        detail = r.text[:500] if r.text else "renderer error"
        raise RuntimeError(f"Browser renderer returned {r.status_code}: {detail}")
    return r.content

def make_pptx(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    max_h = 3800
    scale = min(1.0, 12000 / max(img.width, 1))
    if scale != 1:
        img = img.resize((int(img.width * scale), int(img.height * scale)))
    # Slice the long page into readable presentation-sized sections.
    slice_h = max_h
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    first = True
    y = 0
    while y < img.height:
        h = min(slice_h, img.height - y)
        crop = img.crop((0, y, img.width, y + h))
        bio = io.BytesIO()
        crop.save(bio, format="PNG", optimize=True)
        bio.seek(0)
        if first:
            slide = prs.slides[0]
            first = False
        else:
            slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.shapes.add_picture(bio, 0, 0, width=prs.slide_width, height=prs.slide_height)
        y += h
    out = io.BytesIO()
    prs.save(out)
    return out.getvalue()

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        try:
            from urllib.parse import parse_qs
            qs = parse_qs(urlparse(self.path).query)
            target = qs.get("url", [""])[0].strip()
            fmt = qs.get("format", ["png"])[0].lower()
            width = max(320, min(2560, int(qs.get("width", ["1440"])[0])))
            delay = max(0, min(15, int(qs.get("delay", ["3"])[0])))
            paper = qs.get("paper", ["A4"])[0]
            if not target or urlparse(target).scheme not in ("http", "https") or not urlparse(target).netloc:
                return bad(self, "Enter a valid public http:// or https:// URL.")
            if fmt not in ("png", "jpeg", "pdf", "pptx"):
                return bad(self, "Unsupported format.")
            token = os.environ.get("BROWSERLESS_TOKEN")
            if not token:
                return bad(self, "BROWSERLESS_TOKEN is not configured on the rendering service.", 503)
            if fmt == "pptx":
                raw = browserless(target, "png", width, delay, paper, token)
                data = make_pptx(raw)
                content_type, ext = "application/vnd.openxmlformats-officedocument.presentationml.presentation", "pptx"
            else:
                data = browserless(target, fmt, width, delay, paper, token)
                content_type = "application/pdf" if fmt == "pdf" else ("image/jpeg" if fmt == "jpeg" else "image/png")
                ext = fmt
            host = re.sub(r"^www\.", "", urlparse(target).netloc).replace(":", "-")
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Disposition", f'attachment; filename="snapshot-{host}.{ext}"')
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        except ValueError:
            bad(self, "Invalid numeric capture option.")
        except requests.Timeout:
            bad(self, "Renderer timed out while loading the website.", 504)
        except Exception as exc:
            bad(self, str(exc)[:600], 502)
